# The project include hook runs before upstream adds its compiler options.
# Delay only the Windows adapter so it inherits the final directory options.
if(NOT WIN32 OR CMAKE_VERSION VERSION_LESS 3.19)
    message(FATAL_ERROR "V1 Windows target injection requires Windows and CMake >= 3.19")
endif()
set_property(GLOBAL PROPERTY HELIX_V1_WINDOWS_TARGET_INJECTION
    "${CMAKE_CURRENT_LIST_DIR}/add-target.cmake")
function(_helix_v1_windows_add_target)
    get_property(_helix_v1_target_file GLOBAL PROPERTY HELIX_V1_WINDOWS_TARGET_INJECTION)
    include("${_helix_v1_target_file}")
endfunction()
cmake_language(DEFER CALL _helix_v1_windows_add_target)
