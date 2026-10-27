// Separate native geometry preparation, never slicing or qualification.
// Uses the already source-pinned temperature() setup in main.cpp.
#include "libslic3r/Format/STL.hpp"

static void emit_temperature_geometry(Model &model, const json &request,
                                      const json &snapshot, const fs::path &output)
{
    if (request.at("calibration") != "temperature" || model.objects.size() != 1 ||
        model.objects[0]->instances.size() != 1 || model.objects[0]->volumes.size() != 1)
        throw std::runtime_error("One native Temperature object/volume/instance required");
    const auto path = output / "model.stl";
    const auto receipt = output / "temperature-geometry.json";
    if (fs::exists(path) || fs::exists(receipt))
        throw std::runtime_error("Refusing to overwrite native Temperature geometry");
    auto *object = model.objects[0];
    // The stock CLI performs final bed placement. Avoid baking bed X/Y into
    // float STL coordinates and then subtracting it a second time on import.
    auto matrix = object->instances[0]->get_matrix();
    matrix.translation().x() = 0;
    matrix.translation().y() = 0;
    TriangleMesh mesh = object->raw_mesh();
    mesh.transform(matrix);
    const auto bounds = mesh.bounding_box();
    if (mesh.its.indices.empty() || !bounds.min.allFinite() || !bounds.max.allFinite() ||
        bounds.size().minCoeff() <= 0 || mesh.volume() <= 0)
        throw std::runtime_error("Native Temperature geometry is not a finite positive solid");
    if (!store_stl(path.string().c_str(), &mesh, true))
        throw std::runtime_error("Native Temperature STL export failed");
    const json report = {
        {"schema", "helix-orca-v1-native-temperature-geometry/v1"},
        {"source_commit", source_commit}, {"calibration", "temperature"},
        {"request_id", request.at("request_id")}, {"origin_id", request.at("origin_id")},
        {"context_sha256", request.at("context_sha256")},
        {"parameters", request.at("parameters")}, {"nozzle_mm", snapshot.at("nozzle_mm")},
        {"model", "model.stl"}, {"triangles", mesh.its.indices.size()},
        {"lower_mm", {bounds.min.x(), bounds.min.y(), bounds.min.z()}},
        {"upper_mm", {bounds.max.x(), bounds.max.y(), bounds.max.z()}},
        {"signed_volume_mm3", mesh.volume()}, {"gcode_generated", false},
        {"qualified", false}, {"not_applied", true}
    };
    std::ofstream stream(receipt);
    stream << report.dump(2) << '\n';
    if (!stream) throw std::runtime_error("Native Temperature metadata export failed");
    std::cout << report.dump() << '\n';
}
