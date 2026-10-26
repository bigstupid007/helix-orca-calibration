// Calibration setup derived from OrcaSlicer Plater.cpp at the pinned commit.
// OrcaSlicer source license: GNU Affero General Public License, version 3.
// https://github.com/OrcaSlicer/OrcaSlicer/blob/b5e9cb3c5e7a925adf8379366ae580e4dabb1d03/LICENSE.txt
// Separate, source-pinned adapter. No Orca application source is modified.
// Experimental until compiled and independently compared with native UI output.
#if defined(__linux__) && defined(__x86_64__)
#define HELIX_NATIVE_LINUX_X64 1
#elif defined(_WIN64) && (defined(_M_X64) || defined(__x86_64__))
#define HELIX_NATIVE_WINDOWS_X64 1
#else
#error This registered V1 native build target requires Linux x86_64 or Windows AMD64; other targets need their own audited registration.
#endif
// Match the upstream headless profile validator: define these implementations
// before native headers can include NanoSVG's guarded declarations.
#define NANOSVG_IMPLEMENTATION
#include "nanosvg/nanosvg.h"
#define NANOSVGRAST_IMPLEMENTATION
#include "nanosvg/nanosvgrast.h"
#include "libslic3r/Arrange.hpp"
#include "libslic3r/BuildVolume.hpp"
#include "libslic3r/TriangleMesh.hpp"
#include "libslic3r/CutUtils.hpp"
#include "libslic3r/Flow.hpp"
#include "libslic3r/Model.hpp"
#include "libslic3r/Print.hpp"
#include "libslic3r/PrintConfig.hpp"
#include "libslic3r/Utils.hpp"
#include "libslic3r/calib.hpp"
#include "libslic3r/GCode/GCodeProcessor.hpp"
#include <nlohmann/json.hpp>
#include <tbb/global_control.h>
#include <tbb/task_arena.h>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <csignal>
#if defined(HELIX_NATIVE_LINUX_X64)
#include <execinfo.h>
#include <unistd.h>
#endif
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

using namespace Slic3r;
using json = nlohmann::json;
namespace fs = std::filesystem;
static constexpr const char *source_commit = "b5e9cb3c5e7a925adf8379366ae580e4dabb1d03";
static void diagnostic(const std::string &stage)
{
    if(std::getenv("HELIX_NATIVE_DIAGNOSTICS")) std::cerr<<"native-stage: "<<stage<<std::endl;
}
#if defined(HELIX_NATIVE_LINUX_X64)
static void diagnostic_stack(int)
{
    void *frames[40];
    const int count=backtrace(frames,40);
    backtrace_symbols_fd(frames,count,STDERR_FILENO);
}
#endif

static json registered_target()
{
#if defined(HELIX_NATIVE_WINDOWS_X64)
    return {{"system","Windows"},{"architecture","x86_64"},{"format","PE32+-LE-AMD64"}};
#else
    return {{"system","Linux"},{"architecture","x86_64"},{"format","ELF64-LE-EM_X86_64"}};
#endif
}

static json read_json(const fs::path &path)
{
    if (!fs::is_regular_file(path) || fs::file_size(path) > 1048576)
        throw std::runtime_error("Bounded JSON input required");
    std::ifstream input(path);
    json value = json::parse(input);
    return value;
}

static double number(const json &value, double minimum, double maximum)
{
    if (!value.is_number()) throw std::runtime_error("Numeric parameter required");
    const double result = value.get<double>();
    if (!std::isfinite(result) || result < minimum || result > maximum)
        throw std::runtime_error("Parameter outside V1 native adapter bounds");
    return result;
}

static DynamicPrintConfig retained_config(const json &snapshot)
{
    const bool current=snapshot.at("schema")=="helix-orca-v1-context/v2";
    if ((!current && snapshot.at("schema") != "helix-orca-v1-context/v1") ||
        snapshot.at("runtime").at("version") != "2.5.0-dev" ||
        snapshot.at("runtime").at("build") != (current ? "b5e9cb3c" : "6a7763f0"))
        throw std::runtime_error("Approved pinned retained context required");
    const auto &effective = snapshot.at("effective");
    if (!effective.is_object()) throw std::runtime_error("Effective config unavailable");
    auto required = DynamicPrintConfig::full_print_config();
    DynamicPrintConfig config;
    diagnostic("config-required-inventory");
    // GUI-only bed asset paths are deliberately redacted from retained context.
    // PrintConfig.cpp 1037/1043 define them; no executable slicing consumes them.
    required.erase("bed_custom_model");required.erase("bed_custom_texture");
    // Static enum-list defaults can carry null lookup maps. Keep them only as
    // an inventory; the fresh dynamic config creates each option through its
    // real native definition, which attaches the enum lookup map. Every value
    // still comes from the retained effective snapshot, with no fallback.
    for (const auto &key : required.keys()) {
        if (!effective.contains(key) || !effective.at(key).is_string())
            throw std::runtime_error("Effective value unavailable: " + key);
    }
    for (auto it = effective.begin(); it != effective.end(); ++it) {
        if (!it.value().is_string()) throw std::runtime_error("Serialized config required");
        diagnostic("config-key "+it.key());
        config.set_deserialize_strict(it.key(), it.value().get<std::string>());
    }
    diagnostic("config-deserialized");
    for (const std::string key : {"plugins", "post_process", "slicing_pipeline_plugin"}) {
        if (const auto *option = config.option<ConfigOptionStrings>(key))
            for (const auto &value : option->values)
                if (!value.empty()) throw std::runtime_error("External processing unsupported: " + key);
    }
    const auto *nozzles = config.option<ConfigOptionFloats>("nozzle_diameter");
    if (!nozzles || nozzles->values.empty() || nozzles->get_at(0) <= 0 ||
        std::any_of(nozzles->values.begin(),nozzles->values.end(),[&](double value){return value!=nozzles->get_at(0);}))
        throw std::runtime_error("Native adapter requires one unambiguous nozzle diameter");
    const auto *filaments = config.option<ConfigOptionFloats>("filament_diameter");
    const auto *ratios = config.option<ConfigOptionFloats>("filament_flow_ratio");
    if (!filaments || filaments->values.empty() || !ratios || ratios->values.size()!=filaments->values.size())
        throw std::runtime_error("Native adapter requires complete retained filament slots");
    if(current) {
        const int slot=snapshot.at("origin_filament").at("slot_number").get<int>();
        if(slot<1 || size_t(slot)>filaments->values.size())
            throw std::runtime_error("Originating filament slot is outside the effective config");
    }
    if (config.has("belt_printer") && config.opt_bool("belt_printer"))
        throw std::runtime_error("Belt calibration is outside this adapter qualification");
    return config;
}

// Plater.cpp:1398. The retained effective configuration contains the exact
// edited printer keys that the GUI passes separately as printer_config.
static bool has_junction_deviation(const DynamicPrintConfig &printer_config)
{
    const auto *flavor=printer_config.option<ConfigOptionEnum<GCodeFlavor>>("gcode_flavor");
    const auto *maximum=printer_config.option<ConfigOptionFloats>("machine_max_junction_deviation");
    return flavor&&flavor->value==GCodeFlavor::gcfMarlinFirmware&&maximum&&
           !maximum->values.empty()&&maximum->values.front()>0.0;
}

static void cut(Model &model, double z, ModelObjectCutAttribute keep)
{
    if (model.objects.size() != 1 || model.objects[0]->instances.size() != 1)
        throw std::runtime_error("Native tower requires one object and instance");
    auto *object = model.objects[0];
    const Vec3d offset = object->instances[0]->get_offset();
    Cut cutter(object, 0, Geometry::translation_transform(z * Vec3d::UnitZ() - offset), keep);
    const auto &parts = cutter.perform_with_plane();
    if (parts.size() != 1) throw std::runtime_error("Unexpected native cut result");
    model.delete_object(size_t(0));
    model.add_object(*parts[0]);
    model.objects[0]->ensure_on_bed();
}

static void model_asset(Model &model, const DynamicPrintConfig &config,
                        const fs::path &resources, const char *asset)
{
    // Plater load_files loads mesh assets without default instances, then
    // load_model_objects sorts/centers their volumes before adding and placing
    // the instance. Cut must see those same volume/instance transforms.
    auto input = resources / asset;
#ifdef _WIN32
    // Match Plater::load_files: the DRC loader splits object names on the
    // native separator. Mixed separators would change executable object names.
    input.make_preferred();
#endif
    model = Model::read_from_file(input.string(),nullptr,nullptr,LoadStrategy::LoadModel);
    if (model.objects.size() != 1 || !model.objects[0]->instances.empty())
        throw std::runtime_error("Expected one unplaced native tower asset");
    auto *object=model.objects[0];
    object->sort_volumes(true);
    object->center_around_origin();
    const auto bed=get_extents(config.option<ConfigOptionPoints>("printable_area")->values);
    object->add_instance()->set_offset(Vec3d(bed.center().x(),bed.center().y(),-object->origin_translation(2)));
    object->ensure_on_bed();
}

static void temperature(Model &model, DynamicPrintConfig &config, Calib_Params &params,
                        const json &parameters, const fs::path &resources)
{
    params.start = number(parameters.at("start"), 160, 500);
    params.end = number(parameters.at("end"), 155, 495);
    params.step = number(parameters.at("step"), 5, 5);
    params.nozzle_based_resize = parameters.at("scale").get<bool>();
    if (std::fmod(params.start,5) || std::fmod(params.end,5) || params.start < params.end+5)
        throw std::runtime_error("Native temperature needs descending multiples of five");
    params.mode = CalibMode::Calib_Temp_Tower;
    model_asset(model, config, resources, "calib/temperature_tower/temperature_tower.drc");
    const double top = std::lround((500-params.end)/5+1)*10-EPSILON;
    if (top < model.objects[0]->bounding_box_exact().size().z()) cut(model,top,ModelObjectCutAttribute::KeepLower);
    const double bottom = std::lround((500-params.start)/5)*10+EPSILON;
    if (params.start < 500) cut(model,bottom,ModelObjectCutAttribute::KeepUpper);
    const double nozzle = config.option<ConfigOptionFloats>("nozzle_diameter")->get_at(0);
    auto *object = model.objects[0];
    if (params.nozzle_based_resize && std::abs(nozzle/0.4-1) > EPSILON)
        object->scale(nozzle/0.4,nozzle/0.4,nozzle/0.4);
    object->ensure_on_bed();
    config.set_key_value("resonance_avoidance",new ConfigOptionBool(false));
    config.set_key_value("nozzle_temperature_initial_layer",new ConfigOptionInts(1,std::lround(params.start)));
    config.set_key_value("nozzle_temperature",new ConfigOptionInts(1,std::lround(params.start)));
    config.set_key_value("enable_wrapping_detection",new ConfigOptionBool(false));
    if (params.nozzle_based_resize) {
        object->config.set_key_value("layer_height",new ConfigOptionFloat(nozzle/2));
        config.set_key_value("initial_layer_print_height",new ConfigOptionFloat(nozzle/2));
    }
    object->config.set_key_value("brim_type",new ConfigOptionEnum<BrimType>(btOuterOnly));
    object->config.set_key_value("brim_width",new ConfigOptionFloat(5));
    object->config.set_key_value("brim_object_gap",new ConfigOptionFloat(0));
    object->config.set_key_value("alternate_extra_wall",new ConfigOptionBool(false));
    object->config.set_key_value("seam_slope_type",new ConfigOptionEnum<SeamScarfType>(SeamScarfType::None));
    object->config.set_key_value("overhang_reverse",new ConfigOptionBool(false));
    object->config.set_key_value("precise_z_height",new ConfigOptionBool(false));
}

#include "temperature_prepare.hpp"

static void tower_range(Calib_Params &params,const json &parameters,bool volumetric)
{
    params.start=number(parameters.at("start"),volumetric?std::numeric_limits<double>::min():0,
                        std::numeric_limits<double>::max());
    params.end=number(parameters.at("end"),volumetric?std::numeric_limits<double>::min():0,
                      std::numeric_limits<double>::max());
    params.step=number(parameters.at("step"),std::numeric_limits<double>::min(),
                       std::numeric_limits<double>::max());
    if(params.end<params.start+params.step)
        throw std::runtime_error("Native tower End must be at least Start + Step");
}

static void retraction(Model &model,DynamicPrintConfig &config,Calib_Params &params,
                       const json &parameters,const fs::path &resources)
{
    tower_range(params,parameters,false);
    params.mode=CalibMode::Calib_Retraction_tower;
    model_asset(model,config,resources,"calib/retraction/retraction_tower.drc");
    const double nozzle=config.option<ConfigOptionFloats>("nozzle_diameter")->get_at(0);
    const float native_nozzle=float(nozzle);
    const double height=native_nozzle<=0.1f?0.05f:(native_nozzle<=0.2f?0.1f:0.2f);
    for(auto &value:config.option<ConfigOptionFloats>("max_layer_height")->values)
        value=std::max(value,height);
    config.set_key_value("enable_wrapping_detection",new ConfigOptionBool(false));
    config.set_key_value("wipe_inward",new ConfigOptionBool(false));
    config.set_key_value("resonance_avoidance",new ConfigOptionBool(false));
    config.set_key_value("use_firmware_retraction",new ConfigOptionBool(false));
    config.set_key_value("initial_layer_print_height",new ConfigOptionFloat(height));
    auto &object=model.objects[0]->config;
    object.set_key_value("wall_loops",new ConfigOptionInt(2));
    object.set_key_value("top_shell_layers",new ConfigOptionInt(0));
    object.set_key_value("bottom_shell_layers",new ConfigOptionInt(3));
    object.set_key_value("sparse_infill_density",new ConfigOptionPercent(0));
    object.set_key_value("layer_height",new ConfigOptionFloat(height));
    object.set_key_value("alternate_extra_wall",new ConfigOptionBool(false));
    object.set_key_value("seam_position",new ConfigOptionEnum<SeamPosition>(spAligned));
    object.set_key_value("wall_sequence",new ConfigOptionEnum<WallSequence>(WallSequence::InnerOuter));
    object.set_key_value("overhang_reverse",new ConfigOptionBool(false));
    object.set_key_value("precise_z_height",new ConfigOptionBool(false));
    object.set_key_value("seam_slope_type",new ConfigOptionEnum<SeamScarfType>(SeamScarfType::None));
    const double top=1.4+(params.end-params.start)/params.step-EPSILON;
    if(top>model.objects[0]->bounding_box_exact().size().z()+EPSILON)
        throw std::runtime_error("Requested range exceeds native retraction asset");
    if(top<model.objects[0]->bounding_box_exact().size().z()) cut(model,top,ModelObjectCutAttribute::KeepLower);
}

static void volumetric(Model &model,DynamicPrintConfig &config,Calib_Params &params,
                       const json &parameters,const fs::path &resources)
{
    tower_range(params,parameters,true);
    params.mode=CalibMode::Calib_Vol_speed_Tower;
    model_asset(model,config,resources,"calib/volumetric_speed/SpeedTestStructure.drc");
    auto *object=model.objects[0];
    const auto bed=get_extents(config.option<ConfigOptionPoints>("printable_area")->values);
    const double fit=(bed.size().x()-10)/object->bounding_box_exact().size().x();
    if(fit<=0) throw std::runtime_error("Printable area cannot fit native tower");
    if(fit<1) object->scale(fit,1,1);
    const double nozzle=config.option<ConfigOptionFloats>("nozzle_diameter")->get_at(0);
    const double width=nozzle*1.75,height=nozzle*0.8;
    for(auto &value:config.option<ConfigOptionFloats>("max_layer_height")->values) value=std::max(value,height);
    auto *maximum=config.option<ConfigOptionFloats>("filament_max_volumetric_speed");
    for(auto &value:maximum->values) value=std::max(value,200.0);
    config.set_key_value("slow_down_layer_time",new ConfigOptionFloats{0.0});
    config.set_key_value("resonance_avoidance",new ConfigOptionBool(false));
    config.set_key_value("timelapse_type",new ConfigOptionEnum<TimelapseType>(tlTraditional));
    config.set_key_value("spiral_mode",new ConfigOptionBool(true));
    config.set_key_value("max_volumetric_extrusion_rate_slope",new ConfigOptionFloat(0));
    config.set_key_value("enable_wrapping_detection",new ConfigOptionBool(false));
    auto &cfg=object->config;
    cfg.set_key_value("enable_overhang_speed",new ConfigOptionBoolsNullable(1,false));
    cfg.set_key_value("wall_loops",new ConfigOptionInt(1));
    cfg.set_key_value("alternate_extra_wall",new ConfigOptionBool(false));
    cfg.set_key_value("top_shell_layers",new ConfigOptionInt(0));
    cfg.set_key_value("bottom_shell_layers",new ConfigOptionInt(0));
    cfg.set_key_value("sparse_infill_density",new ConfigOptionPercent(0));
    cfg.set_key_value("outer_wall_line_width",new ConfigOptionFloatOrPercent(width,false));
    cfg.set_key_value("layer_height",new ConfigOptionFloat(height));
    cfg.set_key_value("brim_type",new ConfigOptionEnum<BrimType>(btOuterAndInner));
    cfg.set_key_value("brim_width",new ConfigOptionFloat(5));
    cfg.set_key_value("brim_object_gap",new ConfigOptionFloat(0));
    cfg.set_key_value("precise_z_height",new ConfigOptionBool(false));
    const double top=(params.end-params.start+1)/params.step;
    // Pinned Plater::calib_max_vol_speed only cuts an in-range request.  If
    // the requested height exceeds the stock asset it keeps the complete
    // native tower and still attempts the final slice.
    if(top<object->bounding_box_exact().size().z()) cut(model,top,ModelObjectCutAttribute::KeepLower);
    const double ratio=config.option<ConfigOptionFloats>("filament_flow_ratio")->get_at(params.extruder_id);
    const double volume=Flow(width,height,nozzle).mm3_per_mm()*ratio;
    if(!std::isfinite(volume)||volume<=0) throw std::runtime_error("Effective flow unavailable");
    params.start/=volume;params.end/=volume;params.step/=volume;
}

// Plater::_calib_pa_pattern/_calib_pa_pattern_gen_gcode, exact pinned source.
// One default-speed/default-acceleration pattern; no batch-mode reinterpretation.
static void pressure_advance(Model &model,DynamicPrintConfig &config,Calib_Params &params,
                             const json &parameters)
{
    params.start=number(parameters.at("start"),0,std::numeric_limits<double>::max());
    params.end=number(parameters.at("end"),0,std::numeric_limits<double>::max());
    params.step=number(parameters.at("step"),std::numeric_limits<double>::min(),std::numeric_limits<double>::max());
    if(params.end<params.start+params.step)
        throw std::runtime_error("Native PA End must be at least Start + Step");
    if(parameters.contains("accelerations") || parameters.contains("speeds")) {
        const auto &accelerations=parameters.at("accelerations"),&speeds=parameters.at("speeds");
        if(!accelerations.is_array() || !speeds.is_array() || accelerations.size()>64 || speeds.size()>64)
            throw std::runtime_error("Native PA batch values are malformed");
        int minimum_accel=std::numeric_limits<int>::max(),maximum_speed=0;
        for(const auto &item:accelerations) {const int value=item.get<int>();if(value<=0)throw std::runtime_error("PA accelerations must be positive");minimum_accel=std::min(minimum_accel,value);params.accelerations.push_back(value);}
        for(const auto &item:speeds) {const int value=item.get<int>();if(value<=0)throw std::runtime_error("PA speeds must be positive");maximum_speed=std::max(maximum_speed,value);params.speeds.push_back(value);}
        if(!accelerations.empty()&&!speeds.empty()&&minimum_accel<=maximum_speed)
            throw std::runtime_error("PA accelerations must exceed every speed");
    }
    params.mode=CalibMode::Calib_PA_Pattern;params.print_numbers=true;
    for(const std::string key:{"overhang_reverse","precise_z_height","wipe_inward"})
        config.set_key_value(key,new ConfigOptionBool(false));
    // V1 retained context has no vendor object. Klipper proves this is not the
    // Bambu Marlin writer; reject other flavors rather than infer vendor names.
    if(config.option<ConfigOptionEnum<GCodeFlavor>>("gcode_flavor")->value!=gcfKlipper)
        throw std::runtime_error("Native PA currently requires retained Klipper flavor");
    constexpr bool is_bbl_machine=false;
    const double nozzle=config.option<ConfigOptionFloats>("nozzle_diameter")->get_at(0);
    for(const std::string key:{"filament_retract_when_changing_layer","filament_wipe"})
        config.set_key_value(key,new ConfigOptionBoolsNullable(1,false));
    for(const std::string key:{"wipe","retract_when_changing_layer"})
        config.set_key_value(key,new ConfigOptionBools(1,false));
    config.set_key_value("resonance_avoidance",new ConfigOptionBool(false));
    double accel=config.get_abs_value_at("outer_wall_acceleration",params.extruder_id);
    if(accel==0) accel=config.get_abs_value_at("inner_wall_acceleration",params.extruder_id);
    if(accel==0) accel=config.get_abs_value_at("default_acceleration",params.extruder_id);
    if(params.accelerations.empty()) params.accelerations={accel};
    else accel=*std::max_element(params.accelerations.begin(),params.accelerations.end());
    config.set_key_value("outer_wall_acceleration",new ConfigOptionFloatsNullable(1,accel));
    config.set_key_value("print_sequence",new ConfigOptionEnum<PrintSequence>(PrintSequence::ByLayer));
    const bool junction_deviation=has_junction_deviation(config);
    if(!junction_deviation&&config.get_abs_value_at("default_jerk",params.extruder_id)>0) {
        double jerk=config.get_abs_value_at("outer_wall_jerk",params.extruder_id);
        if(jerk==0) jerk=config.get_abs_value_at("inner_wall_jerk",params.extruder_id);
        if(jerk==0) jerk=config.get_abs_value_at("default_jerk",params.extruder_id);
        for(const std::string key:{"default_jerk","outer_wall_jerk","inner_wall_jerk","top_surface_jerk","infill_jerk","travel_jerk"})
            config.set_key_value(key,new ConfigOptionFloatsNullable(1,jerk));
    }
    if(junction_deviation)
        config.set_key_value("default_junction_deviation",new ConfigOptionFloatsNullable(1,0));
    const SuggestedConfigCalibPAPattern suggested;
    for(const auto &item:suggested.floats_pairs)
        config.set_key_value(item.first,new ConfigOptionFloatsNullable(1,item.second[0]));
    for(const auto &item:suggested.nozzle_ratio_pairs)
        config.set_key_value(item.first,new ConfigOptionFloatOrPercent(nozzle*item.second/100,false));
    for(const auto &item:suggested.int_pairs)
        config.set_key_value(item.first,new ConfigOptionInt(item.second));
    config.set_key_value(suggested.brim_pair.first,new ConfigOptionEnum<BrimType>(suggested.brim_pair.second));
    config.set_key_value("enable_wrapping_detection",new ConfigOptionBool(false));
    double speed=CalibPressureAdvance::find_optimal_PA_speed(config,
        config.get_abs_value("line_width",nozzle),config.get_abs_value("layer_height"),0,0);
    if(params.speeds.empty()) {
        params.speeds={speed};
        config.set_key_value("outer_wall_speed",new ConfigOptionFloatsNullable(1,speed));
    }
    else if(params.speeds.size()==1) {
        speed=params.speeds.front();
        config.set_key_value("outer_wall_speed",new ConfigOptionFloatsNullable(1,speed));
    }
    // GUI_ObjectList create_mesh + GLCanvas3D.cpp 6118: axis-aligned primitive
    // side is 10% of the maximum bed dimension, then centered on the plate.
    const auto bed_bounds=get_extents(config.option<ConfigOptionPoints>("printable_area")->values);
    const double side=0.1*std::max(bed_bounds.size().x(),bed_bounds.size().y());
    auto *cube=model.add_object();cube->add_instance();
    const TriangleMesh mesh(its_make_cube(side,side,side));
    cube->add_volume(mesh);cube->translate(-mesh.bounding_box().center());
    cube->config.set_key_value("extruder",new ConfigOptionInt(params.extruder_id+1));
    cube->instances[0]->set_offset(Vec3d(bed_bounds.center().x(),bed_bounds.center().y(),0));
    cube->ensure_on_bed();
    CalibPressureAdvancePattern pattern(params,config,is_bbl_machine,*cube,Vec3d::Zero());
    auto bounds=cube->raw_bounding_box();
    cube->scale((pattern.print_size_x()+4)/bounds.size().x(),
                (pattern.print_size_y()+4)/bounds.size().y(),pattern.max_layer_z()/bounds.size().z());
    arrangement::ArrangeParams arrangement_params;
    const Points bedpts=arrangement::get_shrink_bedpts(&config,arrangement_params);
    arrangement::ArrangePolygons polygons;
    for(size_t index=0;index<params.speeds.size()*params.accelerations.size();++index) {
        arrangement::ArrangePolygon polygon;cube->instances[0]->get_arrange_polygon(&polygon);polygon.bed_idx=0;
        polygons.emplace_back(polygon);
    }
    arrangement::arrange(polygons,bedpts,arrangement_params);
    bounds=cube->raw_bounding_box();
    cube->scale(pattern.handle_xy_size()/bounds.size().x(),pattern.handle_xy_size()/bounds.size().y(),
                pattern.max_layer_z()/bounds.size().z());
    for(size_t index=0;index<polygons.size();++index) {
        if(polygons[index].bed_idx!=0) throw std::runtime_error("Native PA matrix cannot fit one selected plate");
        const double test_speed=params.speeds[index%params.speeds.size()];
        const double test_accel=params.accelerations[index/params.speeds.size()];
        auto *object=index==0?cube:model.add_object(*cube);
        object->name="pa_pattern_"+std::to_string(int(test_speed))+"_"+std::to_string(int(test_accel));
        if(params.speeds.size()>1)
            object->config.set_key_value("outer_wall_speed",new ConfigOptionFloatsNullable(1,test_speed));
        if(params.accelerations.size()>1)
            object->config.set_key_value("outer_wall_acceleration",new ConfigOptionFloatsNullable(1,test_accel));
        object->instances[0]->set_offset(Vec3d(unscale<double>(polygons[index].translation(X)),
            unscale<double>(polygons[index].translation(Y)),0)+pattern.handle_pos_offset());
        object->ensure_on_bed();
    }
    model.calib_pa_pattern=std::make_unique<CalibPressureAdvancePattern>(pattern);
    std::vector<CustomGCode::Info> generated;
    for(auto *object:model.objects)
        generated.emplace_back(pattern.generate_custom_gcodes(config,is_bbl_machine,*object,Vec3d::Zero()));
    model.plates_custom_gcodes[0]=std::move(generated[0]);
    for(size_t item=1;item<generated.size();++item)
        for(size_t layer=0;layer<model.plates_custom_gcodes[0].gcodes.size();++layer)
            model.plates_custom_gcodes[0].gcodes[layer].extra+=generated[item].gcodes[layer].extra;
}

int main(int argc,char **argv)
{
    try {
#if defined(HELIX_NATIVE_LINUX_X64)
        if(std::getenv("HELIX_NATIVE_DIAGNOSTICS")) {
            // Load the unwinder before a diagnostic signal can interrupt native
            // code. Only our explicitly enabled development process handles it.
            void *frame[1];backtrace(frame,1);
            std::signal(SIGUSR1,diagnostic_stack);
        }
#endif
        // Keep the guard alive through Print destruction: an environment hint
        // does not bound oneTBB's scheduler.
        tbb::global_control scheduler_limit(tbb::global_control::max_allowed_parallelism,2);
        if(argc==2 && std::string(argv[1])=="--capabilities") {
            auto defaults=DynamicPrintConfig::full_print_config();
            defaults.erase("bed_custom_model");defaults.erase("bed_custom_texture");
            auto keys=defaults.keys();
            for(const std::string key:{"plugins","post_process","slicing_pipeline_plugin"})
                if(std::find(keys.begin(),keys.end(),key)==keys.end()) keys.push_back(key);
            std::sort(keys.begin(),keys.end());
            std::cout<<json{{"schema","helix-orca-v1-native-capabilities/v1"},
                {"source_commit",source_commit},{"required_effective_keys",keys},
                {"target",registered_target()},
                {"max_parallelism",2},{"temperature_geometry","native-cut-stl-v1"},
                {"routes",{"temperature","pressure_advance_pattern","retraction","max_volumetric_speed"}}}.dump()<<'\n';
            return 0;
        }
        const bool prepare_temperature=argc==6 && std::string(argv[1])=="--prepare-temperature";
        if(argc!=5 && !prepare_temperature)
            throw std::runtime_error("Usage: native [--prepare-temperature] REQUEST_JSON CONTEXT_JSON RESOURCES OUTPUT_DIRECTORY");
        const int first=prepare_temperature?2:1;
        const auto request=read_json(argv[first]),snapshot=read_json(argv[first+1]);
        const bool current=request.at("schema")=="helix-orca-v1-request/v2";
        if((!current && (request.at("schema")!="helix-orca-v1-request/v1" || request.at("not_applied")!=true)) ||
           request.at("origin_id")!=snapshot.at("origin_id"))
            throw std::runtime_error("Correlated pinned request required");
        const std::string calibration=request.at("calibration").get<std::string>();
        if(prepare_temperature && calibration!="temperature")
            throw std::runtime_error("Geometry-only preparation requires a Temperature request");
        const fs::path resources=fs::canonical(argv[first+2]),output=fs::canonical(argv[first+3]);
        const auto gcode=output/"native-calibration.gcode";
        if(fs::exists(gcode)) throw std::runtime_error("Refusing to overwrite native artifact");
        const auto data=output/"native-data";
        if(fs::exists(data)) throw std::runtime_error("Refusing to reuse native runtime data");
        fs::create_directory(data);
        set_resources_dir(resources.string());
        set_data_dir(data.string());
        set_temporary_dir(output.string());
        diagnostic("resources-ready");
        auto config=retained_config(snapshot);
        diagnostic("config-ready");
        Model model;Calib_Params params;
        const int origin_slot=current?snapshot.at("origin_filament").at("slot_number").get<int>():1;
        params.extruder_id=origin_slot-1;
        if(calibration=="temperature") temperature(model,config,params,request.at("parameters"),resources);
        else if(calibration=="retraction") retraction(model,config,params,request.at("parameters"),resources);
        else if(calibration=="pressure_advance_pattern") pressure_advance(model,config,params,request.at("parameters"));
        else if(calibration=="max_volumetric_speed") volumetric(model,config,params,request.at("parameters"),resources);
        else throw std::runtime_error("Native adapter route is not implemented for this calibration");
        if(current) {
            for(auto *object:model.objects)
                object->config.set_key_value("extruder",new ConfigOptionInt(origin_slot));
        }
        diagnostic("model-ready");
        const auto area=config.option<ConfigOptionPoints>("printable_area")->values;
        const double height=config.opt_float("printable_height");
        diagnostic("bed-inputs-ready");
        // Tower import and PA arrangement already perform native placement.
        // Re-centering a cut result would move it independently of native GUI.
        diagnostic("placement-ready");
        BuildVolume bed(area,height,{area},{height});
        diagnostic("bed-ready");
        if(model.update_print_volume_state(bed)!=model.objects.size())
            throw std::runtime_error("Native model exceeds build volume");
        diagnostic("volume-ready");
        if(prepare_temperature) {
            emit_temperature_geometry(model,request,snapshot,output);
            return 0;
        }
        model.curr_plate_index=0;
        diagnostic("print-constructor-start");
        Print print;
        diagnostic("print-ready");
        print.set_status_callback([](const PrintBase::SlicingStatus &status){
            if(status.warning_step!=-1 && status.message_type!=PrintStateBase::SlicingDefaultNotification)
                throw std::runtime_error("Native slicing warning: "+status.text);
        });
        diagnostic("apply-start");
        print.apply(model,config);
        diagnostic("apply-ready");
        print.set_calib_params(params);
        diagnostic("params-ready");
        std::vector<StringObjectException> warnings;
        diagnostic("validate-start");
        const auto error=print.validate(&warnings);
        diagnostic("validate-ready");
        if(!error.string.empty()||!warnings.empty())
            throw std::runtime_error("Native validation rejected preparation: "+error.string);
        if(print.empty()) throw std::runtime_error("Native print is empty");
        Model::setExtruderParams(config,origin_slot);Model::setPrintSpeedTable(config,print.config());
        GCodeProcessorResult processed;
        // Native Thread.cpp's thread-name/locale barrier counts the current
        // arena, not global_control's worker cap. Match both to avoid waiting
        // for unavailable host-arena workers. Keep process/export in that arena.
        tbb::task_arena slicing_arena(2);
        slicing_arena.execute([&] {
            diagnostic("process-start");
            print.process();
            diagnostic("process-ready");
            print.export_gcode(gcode.string(),&processed,nullptr);
            diagnostic("export-ready");
        });
        json processing={{"error_code",processed.gcode_check_result.error_code},{"warnings",json::array()}};
        for(const auto &warning:processed.warnings)
            processing["warnings"].push_back({{"level",warning.level},{"message",warning.msg},
                                               {"error_code",warning.error_code},{"params",warning.params}});
        std::ofstream(output/"native-processing.json")<<processing.dump(2)<<'\n';
        const auto known_warning=[](const auto &warning){
            return warning.error_code=="1000C001" && warning.msg=="bed_temperature_too_high_than_filament";
        };
        const bool unknown_warning=std::any_of(processed.warnings.begin(),processed.warnings.end(),
                                                [&](const auto &warning){return !known_warning(warning);});
        if(processed.gcode_check_result.error_code!=0 || unknown_warning || (!current && !processed.warnings.empty()))
            throw std::runtime_error("Native post-export validation rejected artifact; see native-processing.json");
        json report={{"source_commit",source_commit},{"calibration",calibration},{"parameters",request.at("parameters")},
                     {"request_id",request.at("request_id")},{"origin_id",request.at("origin_id")},
                     {"context_sha256",request.at("context_sha256")},
                     {"artifact",gcode.filename().string()},{"size",fs::file_size(gcode)},
                     {"qualified",false},{"not_applied",!current},
                     {"processing",processing},{"max_parallelism",2},
                     {"excluded_visual_keys",{"bed_custom_model","bed_custom_texture"}}};
        std::ofstream(output/"native-generation.json")<<report.dump(2)<<'\n';
        std::cout<<report.dump()<<'\n';return 0;
    }catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 2;}
}
