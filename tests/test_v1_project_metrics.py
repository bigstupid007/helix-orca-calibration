"""Sanitized scalar inspection preserves private projects and native transforms."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location('v1_project_metrics', Path(__file__).resolve().parents[1]/'scripts/v1-project-metrics.py')
metrics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metrics)
NS = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
PROD = 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'


def tetra(vertices=None, triangles=None):
    vertices = vertices or [(0,0,0), (1,0,0), (0,1,0), (0,0,1)]
    triangles = triangles or [(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
    vs = ''.join('<vertex x="%s" y="%s" z="%s"/>' % point for point in vertices)
    ts = ''.join('<triangle v1="%s" v2="%s" v3="%s"/>' % face for face in triangles)
    return '<mesh><vertices>'+vs+'</vertices><triangles>'+ts+'</triangles></mesh>'


def model(resources, build):
    return ('<model xmlns="'+NS+'" xmlns:p="'+PROD+'" unit="millimeter"><resources>'+resources+'</resources><build>'+build+'</build></model>')


class ProjectMetrics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def archive(self, name, root_model, extras=None):
        path = self.root/name
        with zipfile.ZipFile(path,'w') as archive:
            archive.writestr('3D/3dmodel.model',root_model)
            for key,value in (extras or {}).items():
                archive.writestr(key,value)
        return path

    def test_transformed_component_geometry_and_private_fields_stay_local(self):
        child = model('<object id="1">'+tetra()+'</object>','')
        root = model('<object id="2"><components><component objectid="1" p:path="/3D/Objects/object_1.model" transform="2 0 0 0 3 0 0 0 4 1 2 3"/></components></object>',
                     '<item objectid="2" transform="1 0 0 0 1 0 0 0 1 10 20 30"/>')
        settings = '<config><object id="2"><metadata key="name" value="temperature_tower.drc"/><metadata key="brim_type" value="outer_only"/><metadata key="brim_width" value="5"/><metadata key="brim_object_gap" value="0"/><metadata key="private_path" value="SECRET_LOCAL_PATH"/><metadata key="machine_start_gcode" value="SECRET_HOOK"/></object></config>'
        project = {'nozzle_temperature':['230'],'private_profile_name':'SECRET_PROFILE','brim_type':'no_brim'}
        path=self.archive('native.3mf',root,{'3D/Objects/object_1.model':child,'Metadata/model_settings.config':settings,
                                          'Metadata/project_settings.config':json.dumps(project)})
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        report=metrics.inspect(path)
        self.assertEqual(report['geometry']['world_bounds_mm'],[[11.,13.],[22.,25.],[33.,37.]])
        self.assertAlmostEqual(report['geometry']['signed_mesh_volume_mm3'],4.)
        self.assertEqual(report['geometry']['triangles'],4)
        self.assertEqual(report['geometry']['boundary_edges_by_index'],0)
        self.assertTrue(report['settings']['objects'][0]['name_is_expected_temperature_asset'])
        self.assertEqual(report['settings']['objects'][0]['settings']['brim_width'],5.)
        text=json.dumps(report)
        self.assertNotIn('SECRET',text)
        self.assertNotIn('vertex',text)
        self.assertNotIn('triangle v',text)
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())

    def test_world_transform_rotation_uses_3mf_column_order(self):
        path=self.archive('rotated.3mf',model('<object id="1">'+tetra()+'</object>',
                                            '<item objectid="1" transform="0 1 0 -1 0 0 0 0 1 10 20 30"/>'))
        data=metrics.inspect(path)['geometry']
        self.assertEqual(data['world_bounds_mm'],[[9.,10.],[20.,21.],[30.,31.]])
        self.assertAlmostEqual(data['signed_mesh_volume_mm3'],1/6)

    def test_open_and_nonmanifold_indexed_edges_are_reported(self):
        faces=[(0,2,1),(0,1,3),(0,3,2)]
        path=self.archive('open.3mf',model('<object id="1">'+tetra(triangles=faces)+'</object>','<item objectid="1"/>'))
        self.assertEqual(metrics.inspect(path)['geometry']['boundary_edges_by_index'],3)
        path=self.archive('nonmanifold.3mf',model('<object id="1">'+tetra(triangles=faces+[faces[0],faces[0]])+'</object>','<item objectid="1"/>'))
        self.assertGreater(metrics.inspect(path)['geometry']['nonmanifold_edges_by_index'],0)

    def test_invalid_index_nonfinite_and_external_references_refuse(self):
        cases=[('<object id="1">'+tetra(triangles=[(0,1,99)])+'</object>','<item objectid="1"/>'),
               ('<object id="1">'+tetra(vertices=[('nan',0,0),(1,0,0),(0,1,0),(0,0,1)])+'</object>','<item objectid="1"/>'),
               ('<object id="1"><components><component objectid="1" p:path="../../private.xml"/></components></object>','<item objectid="1"/>')]
        for index,(objects,build) in enumerate(cases):
            with self.subTest(index=index),self.assertRaises(metrics.MetricsError):
                metrics.inspect(self.archive(str(index)+'.3mf',model(objects,build)))

    def test_cycles_and_entities_refuse(self):
        path=self.archive('cycle.3mf',model('<object id="1"><components><component objectid="1"/></components></object>','<item objectid="1"/>'))
        with self.assertRaises(metrics.MetricsError):metrics.inspect(path)
        path=self.archive('dtd.3mf','<!DOCTYPE model [<!ENTITY data SYSTEM "file:///private">]>'+model('<object id="1">'+tetra()+'</object>','<item objectid="1"/>'))
        with self.assertRaises(metrics.MetricsError):metrics.inspect(path)

    def test_two_projects_produce_scalar_comparison_without_qualification(self):
        first=self.archive('first.3mf',model('<object id="1">'+tetra()+'</object>','<item objectid="1"/>'))
        second=self.archive('second.3mf',model('<object id="1">'+tetra()+'</object>','<item objectid="1" transform="2 0 0 0 2 0 0 0 2 0 0 0"/>'))
        report=metrics.compare(first,second)
        self.assertEqual(report['comparison']['world_extents_delta_candidate_minus_native_mm'],[1.,1.,1.])
        self.assertFalse(report['comparison']['qualified'])


if __name__=='__main__':unittest.main()
