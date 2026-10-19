# Windows headless discovery of Orca's real, later-created bundled target.
# The pinned root otherwise creates an expat fallback before deps_src creates
# the same target. Do not create a target here or invent a binary location.
if(NOT WIN32)
    message(FATAL_ERROR "V1 bundled Expat discovery is Windows-only")
endif()
set(EXPAT_INCLUDE_DIR "${PROJECT_SOURCE_DIR}/deps_src/expat")
foreach(_v1_expat_file expat.h xmlparse.c xmlrole.c xmltok.c CMakeLists.txt)
    if(NOT EXISTS "${EXPAT_INCLUDE_DIR}/${_v1_expat_file}")
        message(FATAL_ERROR "Pinned bundled Expat source is unavailable: ${_v1_expat_file}")
    endif()
endforeach()
set(EXPAT_INCLUDE_DIRS "${EXPAT_INCLUDE_DIR}")
set(EXPAT_LIBRARY expat)
set(EXPAT_LIBRARIES expat)
include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(EXPAT REQUIRED_VARS EXPAT_INCLUDE_DIR EXPAT_LIBRARY)
unset(_v1_expat_file)
