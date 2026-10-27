# App-owned target injection: upstream source and build files remain unchanged.
# Pass only to the pinned source root with CMAKE_PROJECT_OrcaSlicer_INCLUDE.
if(NOT TARGET helix_orca_native)
    add_executable(helix_orca_native "${CMAKE_CURRENT_LIST_DIR}/main.cpp")
    target_compile_features(helix_orca_native PRIVATE cxx_std_17)
    target_include_directories(helix_orca_native PRIVATE
        "${PROJECT_SOURCE_DIR}/src" "${PROJECT_SOURCE_DIR}/deps_src")
    # Native public headers use these even though upstream libslic3r links them
    # privately; propagate their verified include/link interfaces explicitly.
    target_link_libraries(helix_orca_native PRIVATE libslic3r boost_libs
        cereal::cereal TBB::tbb OpenSSL::Crypto)
endif()
