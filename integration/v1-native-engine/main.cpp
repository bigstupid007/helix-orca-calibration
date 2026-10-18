// Calibration setup derived from OrcaSlicer Plater.cpp at the pinned commit.
// OrcaSlicer source license: GNU Affero General Public License, version 3.
// https://github.com/OrcaSlicer/OrcaSlicer/blob/6a7763f08d1a175a464a00ce13f0b5a815662fc4/LICENSE.txt
// Separate, source-pinned adapter. No Orca application source is modified.
// Experimental until compiled and independently compared with native UI output.
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
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace Slic3r;
using json = nlohmann::json;
namespace fs = std::filesystem;
static constexpr const char *source_commit = "6a7763f08d1a175a464a00ce13f0b5a815662fc4";

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
    if (snapshot.at("schema") != "helix-orca-v1-context/v1" ||
        snapshot.at("runtime").at("version") != "2.5.0-dev" ||
        snapshot.at("runtime").at("build") != "6a7763f0")
        throw std::runtime_error("Approved October 15 retained context required");
    const auto &effective = snapshot.at("effective");
    if (!effective.is_object()) throw std::runtime_error("Effective config unavailable");
    DynamicPrintConfig config = DynamicPrintConfig::full_print_config();
    // GUI-only bed asset paths are deliberately redacted from retained context.
    // PrintConfig.cpp 1037/1043 define them; no executable slicing consumes them.
    config.erase("bed_custom_model");config.erase("bed_custom_texture");
    // Defaults establish native types, never replace unavailable effective values.
    for (const auto &key : config.keys()) {
        if (!effective.contains(key) || !effective.at(key).is_string())
            throw std::runtime_error("Effective value unavailable: " + key);
    }
    for (auto it = effective.begin(); it != effective.end(); ++it) {
        if (!it.value().is_string()) throw std::runtime_error("Serialized config required");
        config.set_deserialize_strict(it.key(), it.value().get<std::string>());
    }
    for (const std::string key : {"plugins", "post_process", "slicing_pipeline_plugin"}) {
        if (const auto *option = config.option<ConfigOptionStrings>(key))
            for (const auto &value : option->values)
                if (!value.empty()) throw std::runtime_error("External processing unsupported: " + key);
    }
    const auto *nozzles = config.option<ConfigOptionFloats>("nozzle_diameter");
    if (!nozzles || nozzles->values.size() != 1 || nozzles->get_at(0) <= 0)
        throw std::runtime_error("V1 native adapter requires one known nozzle");
    const auto *filaments = config.option<ConfigOptionFloats>("filament_diameter");
    const auto *ratios = config.option<ConfigOptionFloatsNullable>("filament_flow_ratio");
    if (!filaments || filaments->values.size()!=1 || !ratios || ratios->values.size()!=1)
        throw std::runtime_error("V1 native adapter requires one retained filament");
    if (config.has("belt_printer") && config.opt_bool("belt_printer"))
        throw std::runtime_error("Belt calibration is outside this adapter qualification");
    return config;
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

static void model_asset(Model &model, const fs::path &resources, const char *asset)
{
    model = Model::read_from_file((resources / asset).string());
    if (model.objects.size() != 1) throw std::runtime_error("Expected single native tower asset");
    model.add_default_instances();
    model.objects[0]->ensure_on_bed();
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
    model_asset(model, resources, "calib/temperature_tower/temperature_tower.drc");
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

static void tower_range(Calib_Params &params,const json &parameters,bool volumetric)
{
    params.start=number(parameters.at("start"),volumetric?0.01:0,volumetric?200:20);
    params.end=number(parameters.at("end"),volumetric?0.01:0,volumetric?200:20);
    params.step=number(parameters.at("step"),0.001,volumetric?200:20);
    if(params.end<params.start+params.step || (params.end-params.start)/params.step>1000)
        throw std::runtime_error("Unsupported native tower sample count");
}

static void retraction(Model &model,DynamicPrintConfig &config,Calib_Params &params,
                       const json &parameters,const fs::path &resources)
{
    tower_range(params,parameters,false);
    params.mode=CalibMode::Calib_Retraction_tower;
    model_asset(model,resources,"calib/retraction/retraction_tower.drc");
    const double nozzle=config.option<ConfigOptionFloats>("nozzle_diameter")->get_at(0);
    const double height=nozzle<=0.1?0.05:(nozzle<=0.2?0.1:0.2);
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
    model_asset(model,resources,"calib/volumetric_speed/SpeedTestStructure.drc");
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
    if(top>object->bounding_box_exact().size().z()+EPSILON)
        throw std::runtime_error("Requested range exceeds native volumetric asset");
    if(top<object->bounding_box_exact().size().z()) cut(model,top,ModelObjectCutAttribute::KeepLower);
    const double ratio=config.option<ConfigOptionFloatsNullable>("filament_flow_ratio")->get_at(0);
    const double volume=Flow(width,height,nozzle).mm3_per_mm()*ratio;
    if(!std::isfinite(volume)||volume<=0) throw std::runtime_error("Effective flow unavailable");
    params.start/=volume;params.end/=volume;params.step/=volume;
}

// Plater::_calib_pa_pattern/_calib_pa_pattern_gen_gcode, exact pinned source.
// One default-speed/default-acceleration pattern; no batch-mode reinterpretation.
static void pressure_advance(Model &model,DynamicPrintConfig &config,Calib_Params &params,
                             const json &parameters)
{
    params.start=number(parameters.at("start"),0,5);
    params.end=number(parameters.at("end"),0,5);
    params.step=number(parameters.at("step"),0.001,5);
    if(params.end<params.start+params.step || (params.end-params.start)/params.step>1000)
        throw std::runtime_error("Unsupported native PA sample count");
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
    double accel=config.get_abs_value_at("outer_wall_acceleration",0);
    if(accel==0) accel=config.get_abs_value_at("inner_wall_acceleration",0);
    if(accel==0) accel=config.get_abs_value_at("default_acceleration",0);
    config.set_key_value("outer_wall_acceleration",new ConfigOptionFloatsNullable(1,accel));
    config.set_key_value("print_sequence",new ConfigOptionEnum<PrintSequence>(PrintSequence::ByLayer));
    if(config.get_abs_value_at("default_jerk",0)>0) {
        double jerk=config.get_abs_value_at("outer_wall_jerk",0);
        if(jerk==0) jerk=config.get_abs_value_at("inner_wall_jerk",0);
        if(jerk==0) jerk=config.get_abs_value_at("default_jerk",0);
        for(const std::string key:{"default_jerk","outer_wall_jerk","inner_wall_jerk","top_surface_jerk","infill_jerk","travel_jerk"})
            config.set_key_value(key,new ConfigOptionFloatsNullable(1,jerk));
    }
    const SuggestedConfigCalibPAPattern suggested;
    for(const auto &item:suggested.floats_pairs)
        config.set_key_value(item.first,new ConfigOptionFloatsNullable(1,item.second[0]));
    for(const auto &item:suggested.nozzle_ratio_pairs)
        config.set_key_value(item.first,new ConfigOptionFloatOrPercent(nozzle*item.second/100,false));
    for(const auto &item:suggested.int_pairs)
        config.set_key_value(item.first,new ConfigOptionInt(item.second));
    config.set_key_value(suggested.brim_pair.first,new ConfigOptionEnum<BrimType>(suggested.brim_pair.second));
    config.set_key_value("enable_wrapping_detection",new ConfigOptionBool(false));
    const double speed=CalibPressureAdvance::find_optimal_PA_speed(config,
        config.get_abs_value("line_width",nozzle),config.get_abs_value("layer_height"),0,0);
    config.set_key_value("outer_wall_speed",new ConfigOptionFloatsNullable(1,speed));
    // GUI primitive side length is bed-relative; subsequent native bbox scaling
    // cancels its magnitude. Preserve its centered, axis-aligned cube topology.
    auto *cube=model.add_object();cube->add_instance();
    const TriangleMesh mesh(its_make_cube(20,20,20));
    cube->add_volume(mesh);cube->translate(-mesh.bounding_box().center());
    cube->config.set_key_value("extruder",new ConfigOptionInt(1));cube->ensure_on_bed();
    CalibPressureAdvancePattern pattern(params,config,is_bbl_machine,*cube,Vec3d::Zero());
    auto bounds=cube->raw_bounding_box();
    cube->scale((pattern.print_size_x()+4)/bounds.size().x(),
                (pattern.print_size_y()+4)/bounds.size().y(),pattern.max_layer_z()/bounds.size().z());
    arrangement::ArrangeParams arrangement_params;
    const Points bedpts=arrangement::get_shrink_bedpts(&config,arrangement_params);
    arrangement::ArrangePolygon polygon;cube->instances[0]->get_arrange_polygon(&polygon);polygon.bed_idx=0;
    arrangement::ArrangePolygons polygons{polygon};
    arrangement::arrange(polygons,bedpts,arrangement_params);
    if(polygons[0].bed_idx!=0) throw std::runtime_error("Native PA cannot fit selected plate");
    bounds=cube->raw_bounding_box();
    cube->scale(pattern.handle_xy_size()/bounds.size().x(),pattern.handle_xy_size()/bounds.size().y(),
                pattern.max_layer_z()/bounds.size().z());
    cube->name="pa_pattern_"+std::to_string(int(speed))+"_"+std::to_string(int(accel));
    cube->instances[0]->set_offset(Vec3d(unscale<double>(polygons[0].translation(X)),
        unscale<double>(polygons[0].translation(Y)),0)+pattern.handle_pos_offset());
    cube->ensure_on_bed();
    model.calib_pa_pattern=std::make_unique<CalibPressureAdvancePattern>(pattern);
    model.plates_custom_gcodes[0]=pattern.generate_custom_gcodes(config,is_bbl_machine,*cube,Vec3d::Zero());
}

int main(int argc,char **argv)
{
    try {
        if(argc==2 && std::string(argv[1])=="--capabilities") {
            auto defaults=DynamicPrintConfig::full_print_config();
            defaults.erase("bed_custom_model");defaults.erase("bed_custom_texture");
            auto keys=defaults.keys();
            for(const std::string key:{"plugins","post_process","slicing_pipeline_plugin"})
                if(std::find(keys.begin(),keys.end(),key)==keys.end()) keys.push_back(key);
            std::sort(keys.begin(),keys.end());
            std::cout<<json{{"schema","helix-orca-v1-native-capabilities/v1"},
                {"source_commit",source_commit},{"required_effective_keys",keys},
                {"routes",{"temperature","pressure_advance_pattern","retraction","max_volumetric_speed"}}}.dump()<<'\n';
            return 0;
        }
        if(argc!=5) throw std::runtime_error("Usage: native REQUEST_JSON CONTEXT_JSON RESOURCES OUTPUT_DIRECTORY");
        const auto request=read_json(argv[1]),snapshot=read_json(argv[2]);
        if(request.at("schema")!="helix-orca-v1-request/v1" || request.at("not_applied")!=true ||
           request.at("origin_id")!=snapshot.at("origin_id"))
            throw std::runtime_error("Correlated V1 request required");
        const std::string calibration=request.at("calibration").get<std::string>();
        const fs::path resources=fs::canonical(argv[3]),output=fs::canonical(argv[4]);
        const auto gcode=output/"native-calibration.gcode";
        if(fs::exists(gcode)) throw std::runtime_error("Refusing to overwrite native artifact");
        const auto data=output/"native-data";
        if(fs::exists(data)) throw std::runtime_error("Refusing to reuse native runtime data");
        fs::create_directory(data);
        set_resources_dir(resources.string());
        set_data_dir(data.string());
        set_temporary_dir(output.string());
        auto config=retained_config(snapshot);
        Model model;Calib_Params params;
        if(calibration=="temperature") temperature(model,config,params,request.at("parameters"),resources);
        else if(calibration=="retraction") retraction(model,config,params,request.at("parameters"),resources);
        else if(calibration=="pressure_advance_pattern") pressure_advance(model,config,params,request.at("parameters"));
        else if(calibration=="max_volumetric_speed") volumetric(model,config,params,request.at("parameters"),resources);
        else throw std::runtime_error("Native adapter route is not implemented for this calibration");
        const auto area=config.option<ConfigOptionPoints>("printable_area")->values;
        const double height=config.opt_float("printable_height");
        if(calibration!="pressure_advance_pattern") model.center_instances_around_point(get_extents(area).center());
        BuildVolume bed(area,height,{area},{height});
        if(model.update_print_volume_state(bed)!=model.objects.size())
            throw std::runtime_error("Native model exceeds build volume");
        model.curr_plate_index=0;
        Print print;
        print.set_status_callback([](const PrintBase::SlicingStatus &status){
            if(status.warning_step!=-1 && status.message_type!=PrintStateBase::SlicingDefaultNotification)
                throw std::runtime_error("Native slicing warning: "+status.text);
        });
        print.apply(model,config);print.set_calib_params(params);
        std::vector<StringObjectException> warnings;
        const auto error=print.validate(&warnings);
        if(!error.string.empty()||!warnings.empty())
            throw std::runtime_error("Native validation rejected preparation: "+error.string);
        if(print.empty()) throw std::runtime_error("Native print is empty");
        Model::setExtruderParams(config,1);Model::setPrintSpeedTable(config,print.config());
        print.process();
        print.export_gcode(gcode.string(),nullptr,nullptr);
        json report={{"source_commit",source_commit},{"calibration",calibration},{"parameters",request.at("parameters")},
                     {"request_id",request.at("request_id")},{"origin_id",request.at("origin_id")},
                     {"context_sha256",request.at("context_sha256")},
                     {"artifact",gcode.filename().string()},{"size",fs::file_size(gcode)},
                     {"qualified",false},{"not_applied",true},
                     {"excluded_visual_keys",{"bed_custom_model","bed_custom_texture"}}};
        std::ofstream(output/"native-generation.json")<<report.dump(2)<<'\n';
        std::cout<<report.dump()<<'\n';return 0;
    }catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 2;}
}
