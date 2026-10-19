"""Real CMake graph checks; Linux WIN32 simulation is not Windows qualification."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1]/'integration/v1-native-engine/windows-cmake'


@unittest.skipUnless(shutil.which('cmake') and shutil.which('cc'), 'CMake/C compiler unavailable')
class BundledExpatDiscovery(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root/'source'
        self.bundled = self.source/'deps_src/expat'
        self.bundled.mkdir(parents=True)
        for name in ('expat.h', 'xmlparse.c', 'xmlrole.c', 'xmltok.c'):
            (self.bundled/name).write_text('/* synthetic build-graph fixture only */\n')
        (self.bundled/'xmlparse.c').write_text('int v1_expat_fixture(void) { return 7; }\n')
        (self.bundled/'CMakeLists.txt').write_text('add_library(expat STATIC xmlparse.c xmlrole.c xmltok.c)\n')
        (self.source/'main.c').write_text('int v1_expat_fixture(void); int main(void) { return v1_expat_fixture()!=7; }\n')
        (self.source/'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.13)
project(expat_conflict_reproducer C)
set(WIN32 TRUE) # selection simulation; the host compiler remains Linux
find_package(EXPAT QUIET MODULE)
if(NOT EXPAT_FOUND)
  add_library(expat STATIC deps_src/expat/xmlparse.c)
endif()
add_subdirectory(deps_src/expat)
add_executable(consumer main.c)
target_link_libraries(consumer PRIVATE ${EXPAT_LIBRARIES})
get_target_property(kind expat TYPE)
if(NOT kind STREQUAL "STATIC_LIBRARY")
  message(FATAL_ERROR "Bundled Expat is not a real static target")
endif()
''')

    def configure(self, module):
        return subprocess.run(['cmake', '-S', str(self.source), '-B', str(self.root/'build'),
            '-DCMAKE_MODULE_PATH='+str(module)], text=True, capture_output=True, timeout=20)

    def test_failed_discovery_reproduces_duplicate_and_owned_module_builds_one_real_target(self):
        absent = self.root/'absent'
        absent.mkdir()
        (absent/'FindEXPAT.cmake').write_text('set(EXPAT_FOUND FALSE)\n')
        failure = self.configure(absent)
        self.assertNotEqual(failure.returncode, 0)
        self.assertIn('another target', failure.stderr)
        shutil.rmtree(self.root/'build')
        result = self.configure(MODULE)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        result = subprocess.run(['cmake', '--build', str(self.root/'build'), '--parallel', '1'],
            text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        result = subprocess.run([str(self.root/'build/consumer')], timeout=5)
        self.assertEqual(result.returncode, 0)

    def test_missing_real_bundled_source_is_fatal(self):
        (self.bundled/'xmltok.c').unlink()
        result = self.configure(MODULE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Pinned bundled Expat source is unavailable: xmltok.c', result.stderr)

    def test_module_refuses_non_windows_configuration(self):
        path = self.source/'CMakeLists.txt'
        path.write_text(path.read_text().replace('set(WIN32 TRUE)', 'set(WIN32 FALSE)'))
        result = self.configure(MODULE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Windows-only', result.stderr)

    def test_deferred_windows_target_inherits_late_upstream_compile_options(self):
        injection = MODULE.parent
        for mode, filename in (('early', 'add-target.cmake'), ('deferred', 'windows-target.cmake')):
            source = self.root/mode
            source.mkdir()
            (source/'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.19)
project(target_option_reproducer CXX)
set(WIN32 TRUE) # property simulation; no Windows compiler or compile claim
add_library(libslic3r INTERFACE)
add_library(boost_libs INTERFACE)
foreach(name cereal::cereal TBB::tbb OpenSSL::Crypto)
  add_library(${name} INTERFACE IMPORTED)
endforeach()
include("'''+str(injection/filename)+'''")
add_compile_options(-DV1_LATE_UPSTREAM_OPTION)
function(capture)
  get_target_property(options helix_orca_native COMPILE_OPTIONS)
  file(WRITE "${CMAKE_BINARY_DIR}/adapter-options.txt" "${options}")
endfunction()
cmake_language(DEFER CALL capture)
''')
            build = self.root/(mode+'-build')
            result = subprocess.run(['cmake', '-S', str(source), '-B', str(build)],
                text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            options = (build/'adapter-options.txt').read_text()
            if mode == 'early':
                self.assertNotIn('V1_LATE_UPSTREAM_OPTION', options)
            else:
                self.assertIn('V1_LATE_UPSTREAM_OPTION', options)


if __name__ == '__main__':
    unittest.main()
