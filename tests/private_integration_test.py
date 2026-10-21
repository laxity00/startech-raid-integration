"""Offline HA API-contract doubles, not a running Home Assistant installation.

Exercises our actual config flow, setup/unload, coordinator, entity creation,
values, diagnostics and client error paths. No hardware or network is accessed.
"""
import asyncio
from copy import deepcopy
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/'custom_components/startech_raid'


def module(name, **values):
    value=types.ModuleType(name);value.__dict__.update(values);value.__path__=[];sys.modules[name]=value
    if '.' in name:
        parent,child=name.rsplit('.',1)
        if parent in sys.modules:setattr(sys.modules[parent],child,value)
    return value


class ClientError(Exception):pass
class ConfigEntryAuthFailed(Exception):pass
class UpdateFailed(Exception):pass
class CoordinatorEntity:
    def __init__(self,coordinator):self.coordinator=coordinator
    @property
    def available(self):return self.coordinator.last_update_success
class DataUpdateCoordinator:
    def __init__(self,hass,logger,**kwargs):self.hass=hass;self.listeners=[];self.data=None;self.last_update_success=True
    async def async_config_entry_first_refresh(self):self.data=await self._async_update_data()
    def async_add_listener(self,callback):
        self.listeners.append(callback)
        return lambda:self.listeners.remove(callback)
class ConfigFlow:
    def __init_subclass__(cls,**kwargs):pass
    async def async_set_unique_id(self,value):self.unique_id=value
    def _abort_if_unique_id_configured(self):self.duplicate_checked=True
    def async_create_entry(self,**kwargs):return dict(type='create_entry',**kwargs)
    def async_show_form(self,**kwargs):return dict(type='form',**kwargs)
    def _get_reconfigure_entry(self):return self.entry
    def _get_reauth_entry(self):return self.entry
    def async_update_reload_and_abort(self,entry,data_updates):
        entry.data=data_updates
        return {'type':'abort','reason':'updated'}


module('aiohttp',ClientError=ClientError,ClientTimeout=lambda **k:k)
module('voluptuous',Schema=lambda v:v,Required=lambda v,**k:v,All=lambda *a:a,Coerce=lambda v:v,Range=lambda **k:k)
module('homeassistant')
module('homeassistant.config_entries',ConfigFlow=ConfigFlow)
module('homeassistant.const',Platform=types.SimpleNamespace(SENSOR='sensor',BINARY_SENSOR='binary_sensor'),EntityCategory=types.SimpleNamespace(DIAGNOSTIC='diagnostic'))
module('homeassistant.exceptions',ConfigEntryAuthFailed=ConfigEntryAuthFailed)
module('homeassistant.helpers')
module('homeassistant.helpers.aiohttp_client',async_get_clientsession=lambda hass:hass.session)
module('homeassistant.helpers.selector',TextSelector=lambda v:v)
module('homeassistant.helpers.update_coordinator',CoordinatorEntity=CoordinatorEntity,DataUpdateCoordinator=DataUpdateCoordinator,UpdateFailed=UpdateFailed)
module('homeassistant.helpers.device_registry',DeviceInfo=lambda **kw:kw)
module('homeassistant.helpers.entity_registry',RegistryEntryDisabler=types.SimpleNamespace(INTEGRATION='integration',USER='user'),async_get=lambda hass:hass.registry,async_entries_for_config_entry=lambda registry,eid:registry)
module('homeassistant.components')
module('homeassistant.components.sensor',SensorEntity=type('SensorEntity',(),{}),SensorDeviceClass=types.SimpleNamespace(ENUM='enum',TEMPERATURE='temperature',DATA_SIZE='data_size',TIMESTAMP='timestamp',DURATION='duration'),SensorStateClass=types.SimpleNamespace(MEASUREMENT='measurement'))
module('homeassistant.components.binary_sensor',BinarySensorEntity=type('BinarySensorEntity',(),{}),BinarySensorDeviceClass=types.SimpleNamespace(PROBLEM='problem'))
module('custom_components')
package=module('custom_components.startech_raid');package.__path__=[str(PKG)]
model=importlib.import_module('custom_components.startech_raid.model')
api=importlib.import_module('custom_components.startech_raid.api')
coordinator_module=importlib.import_module('custom_components.startech_raid.coordinator')
sensor=importlib.import_module('custom_components.startech_raid.sensor')
binary=importlib.import_module('custom_components.startech_raid.binary_sensor')
flow_module=importlib.import_module('custom_components.startech_raid.config_flow')
diagnostics=importlib.import_module('custom_components.startech_raid.diagnostics')
setup_spec=importlib.util.spec_from_file_location('custom_components.startech_raid',PKG/'__init__.py',submodule_search_locations=[str(PKG)])
setup_module=importlib.util.module_from_spec(setup_spec)
sys.modules['custom_components.startech_raid']=setup_module
setup_spec.loader.exec_module(setup_module)


def sample():
    value=json.loads((ROOT/'tests/fixtures/private_app_sample.json').read_text())
    value.update(api_version=1,app_version='0.3.5',instance_id='test-instance',fresh=True,sample_time_unix=int(time.time()),
                 known_ssds=[{k:d.get(k) for k in ['serial','port','model','firmware','capacity_bytes']} for d in value['ssds']],
                 service={'stale_after_seconds':900,'interval_seconds':300,'smart_enabled':True,'smart_paused':False,
                          'temperature_warning_c':65,'duration_ms':100,'next_collection_unix':int(time.time())+300})
    return value


class Response:
    def __init__(self,value,code=200):
        self.status=code;self.body=value if isinstance(value,bytes) else json.dumps(value).encode();self.content=self
    async def __aenter__(self):return self
    async def __aexit__(self,*_):pass
    async def read(self,size):
        chunk,self.body=self.body[:size],self.body[size:]
        return chunk
class Session:
    def __init__(self,value=None,code=200):self.value=value or sample();self.code=code;self.calls=[]
    def get(self,url,**kwargs):
        self.calls.append((url,kwargs))
        return Response(self.value,self.code)
class Entry:
    unique_id='test-instance';entry_id='entry-test'
    def __init__(self):self.data={'host':'local-startech-raid','port':8098,'api_token':'a'*64};self.unload=[]
    def async_on_unload(self,callback):self.unload.append(callback)
class Entries:
    async def async_forward_entry_setups(self,entry,platforms):self.forwarded=platforms
    async def async_unload_platforms(self,entry,platforms):self.unloaded=platforms;return True


class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.data=sample();self.entry=Entry()
        self.hass=types.SimpleNamespace(session=Session(),config_entries=Entries(),registry=[])
        self.coordinator=coordinator_module.StartechCoordinator(self.hass,self.entry,api.Client(self.hass.session,'local-startech-raid',8098,'a'*64))
        self.coordinator.data=self.data

    async def test_client_and_redirect_protection(self):
        result=await self.coordinator.client.status()
        self.assertEqual(result['raid_raw'],1)
        url,kwargs=self.hass.session.calls[0]
        self.assertEqual(url,'http://local-startech-raid:8098/v1/status')
        self.assertFalse(kwargs['allow_redirects'])
        self.assertNotIn('a'*64,url)
        self.assertEqual(kwargs['headers']['Authorization'],'Bearer '+'a'*64)

    async def test_client_auth_status_size_schema(self):
        for code,exception in [(401,api.InvalidAuth),(403,api.InvalidAuth),(302,ValueError),(500,ValueError)]:
            with self.assertRaises(exception):await api.Client(Session(code=code),'host',8098,'a'*64).status()
        for value in [b'not JSON',b'x'*131073,{'api_version':3}]:
            with self.assertRaises(ValueError):await api.Client(Session(value),'host',8098,'a'*64).status()

    async def test_host_and_credential_validation(self):
        for host in ['http://host','host/path','host@other','host\n','', 'a b']:
            with self.assertRaises(ValueError):api.base_url(host,8098)
        self.assertEqual(api.base_url('::1',8098),'http://[::1]:8098')
        with self.assertRaises(ValueError):api.Client(Session(),'host',8098,'short')

    async def test_sensor_values_and_metadata(self):
        created=[]
        await sensor.async_setup_entry(self.hass,types.SimpleNamespace(runtime_data=self.coordinator,async_on_unload=lambda cb:None),lambda values:created.extend(values))
        self.assertEqual(len(created),88)
        self.assertEqual(len({e._attr_unique_id for e in created}),88)
        self.assertEqual(sum(not e._attr_entity_registry_enabled_default for e in created),60)
        temps=[e for e in created if e.spec.kind=='temperature']
        self.assertEqual(len(temps),2)
        self.assertEqual([e.native_value for e in temps],[35,35])
        self.assertTrue(all(e._attr_state_class=='measurement' and e._attr_native_unit_of_measurement=='°C' for e in temps))
        self.assertFalse(temps[0].extra_state_attributes['interpretation_verified'])
        capacity=next(e for e in created if e.spec.kind=='capacity')
        self.assertAlmostEqual(capacity.native_value,256.0)
        self.assertEqual(capacity.extra_state_attributes['capacity_bytes'],256000000000)

    async def test_unavailable_and_no_last_good(self):
        spec=next(s for s in model.DRIVE_SPECS if s.kind=='temperature')
        entity=sensor.StartechSensor(self.coordinator,spec,'TEST-SERIAL-0')
        self.assertTrue(entity.available)
        for mutate in [lambda d:d.update(fresh=False),lambda d:d.update(query_ok=False),lambda d:d.update(duplicate_ssd_identity=True),lambda d:d.update(sample_time_unix=int(time.time())-901),lambda d:d.update(ssds=[])]:
            self.coordinator.data=sample();mutate(self.coordinator.data)
            self.assertFalse(entity.available)
            self.assertIsNone(entity.native_value)
        self.coordinator.data=sample();self.coordinator.last_update_success=False
        self.assertFalse(entity.available)

    async def test_dynamic_drive_change_and_unknown_enum(self):
        created=[]
        await sensor.async_setup_entry(self.hass,types.SimpleNamespace(runtime_data=self.coordinator,async_on_unload=lambda cb:None),lambda values:created.extend(values))
        old=next(e for e in created if e.serial=='TEST-SERIAL-0' and e.spec.kind=='temperature')
        self.coordinator.data['ssds'][0]['serial']='NEW-SERIAL'
        self.coordinator.data['known_ssds'].append(dict(self.coordinator.data['known_ssds'][0],serial='NEW-SERIAL'))
        for callback in self.coordinator.listeners:callback()
        self.assertEqual(len(created),129)
        self.assertFalse(old.available)
        self.coordinator.data.update(raid_raw=255,raid_status='Unknown')
        self.assertEqual(model.sensor_value(self.coordinator.data,model.ARRAY_SPECS[0]),'Unknown')

    async def test_problem_entities(self):
        created=[]
        await binary.async_setup_entry(self.hass,types.SimpleNamespace(runtime_data=self.coordinator,async_on_unload=lambda cb:None),lambda values:created.extend(values))
        self.assertEqual(len(created),12)
        self.assertTrue(all(e.is_on is False for e in created if e.key not in ("media_error_warning","interface_error_warning","life_warning")))
        self.assertTrue(all(e.is_on is None for e in created if e.key in ("media_error_warning","interface_error_warning","life_warning")))
        self.coordinator.data['raid_raw']=2
        self.assertTrue(next(e for e in created if e.key=='raid_problem').is_on)
        self.coordinator.data['ssds'][0]['temperature_candidate_c']=70
        self.assertTrue(next(e for e in created if e.key=='temperature_warning' and e.serial=='TEST-SERIAL-0').is_on)
        self.coordinator.data['query_ok']=False
        self.assertTrue(next(e for e in created if e.key=='collection_problem').is_on)

    async def test_setup_unload_coordinator_errors(self):
        await setup_module.async_setup_entry(self.hass,self.entry)
        self.assertEqual(self.hass.config_entries.forwarded,['sensor','binary_sensor'])
        self.assertTrue(await setup_module.async_unload_entry(self.hass,self.entry))
        self.hass.session.code=401
        with self.assertRaises(ConfigEntryAuthFailed):await self.entry.runtime_data._async_update_data()
        self.hass.session.code=200;self.hass.session.value=dict(sample(),instance_id='different')
        with self.assertRaises(UpdateFailed):await self.entry.runtime_data._async_update_data()

    async def test_flow_setup_and_reconfigure(self):
        flow=flow_module.StartechFlow();flow.hass=self.hass;flow.entry=self.entry
        form=await flow.async_step_user()
        self.assertEqual(form['type'],'form')
        result=await flow.async_step_user(self.entry.data)
        self.assertEqual(result['type'],'create_entry')
        self.assertTrue(flow.duplicate_checked)
        self.hass.session.code=401
        self.assertEqual((await flow.async_step_user(self.entry.data))['errors']['base'],'invalid_auth')
        self.hass.session.code=200
        self.assertEqual((await flow.async_step_reconfigure(self.entry.data))['reason'],'updated')
        self.hass.session.value=dict(sample(),instance_id='different')
        self.assertEqual((await flow.async_step_reconfigure(self.entry.data))['errors']['base'],'identity_changed')
        self.hass.session.value=sample()
        self.assertEqual((await flow.async_step_reauth_confirm(self.entry.data))['reason'],'updated')

    async def test_redacted_diagnostics_and_real_registry_ids(self):
        self.entry.runtime_data=self.coordinator
        self.hass.registry=[types.SimpleNamespace(entity_id='sensor.registered_temperature',unique_id='test-instance_TEST-SERIAL-0_temperature_candidate_c',disabled_by=None)]
        value=await diagnostics.async_get_config_entry_diagnostics(self.hass,self.entry)
        encoded=json.dumps(value)
        self.assertNotIn('TEST-SERIAL',encoded)
        self.assertNotIn('a'*64,encoded)
        self.assertNotIn('test-instance',encoded)
        self.assertEqual(value['dashboard']['views'][0]['cards'][1]['entities'],['sensor.registered_temperature'])


    async def test_profile_labels_warning_boundaries_and_migration(self):
        smart=importlib.import_module('custom_components.startech_raid.smart')
        disk=self.data['ssds'][0]
        disk.update(firmware='Y0507A0',smart_controller_signature='SMI2259XT')
        ids=list(smart.LABELS)
        disk['attributes']=[dict(id=i,raw=0,normalized=100,worst=100,flags=50,threshold=50,raw_hex='000000000000') for i in ids]
        attrs={a['id']:a for a in disk['attributes']}
        attrs[169]['raw']=100
        attrs[163]['raw']=10;attrs[168]['raw']=5050;attrs[195]['raw']=123
        self.assertFalse(model.problem(self.data,'media_error_warning',disk['serial']))
        self.assertFalse(model.problem(self.data,'life_warning',disk['serial']))
        for i in smart.MEDIA_IDS:
            attrs[i]['raw']=1
            self.assertTrue(model.problem(self.data,'media_error_warning',disk['serial']))
            attrs[i]['raw']=0
        for value,expected in [(21,False),(20,True),(0,True),(101,None),(-1,None),(None,None)]:
            attrs[169]['raw']=value
            self.assertIs(model.problem(self.data,'life_warning',disk['serial']),expected)
        attrs[199]['raw']=1
        self.assertTrue(model.problem(self.data,'interface_error_warning',disk['serial']))
        self.assertFalse(model.problem(self.data,'media_error_warning',disk['serial']))
        attrs[5]['raw']=None
        self.assertIsNone(model.problem(self.data,'media_error_warning',disk['serial']))
        disk['smart_data_valid']=False
        self.assertTrue(all(v is None for v in smart.indicators(disk).values()))
        disk['smart_data_valid']=True
        disk['firmware']='OTHER'
        self.assertFalse(smart.metadata(disk,5)['profile_matched'])
        self.assertIsNone(model.problem(self.data,'media_error_warning',disk['serial']))
        disk['firmware']='Y0507A0'
        # Exercise actual platform migration with a registry double: user choices survive.
        records={}
        for i,disabled in [(5,'integration'),(160,'user'),(161,None)]:
            uid=f"test-instance_{disk['serial']}_raw_{i}"
            records[uid]=types.SimpleNamespace(entity_id=f'sensor.existing_{i}',config_entry_id='entry-test',disabled_by=disabled)
        class Registry:
            def async_get_entity_id(self,domain,platform,uid):
                return records[uid].entity_id if uid in records else None
            def async_get(self,eid):return next(e for e in records.values() if e.entity_id==eid)
            def async_update_entity(self,eid,**kwargs):
                for k,v in kwargs.items():setattr(self.async_get(eid),k,v)
        self.hass.registry=Registry()
        created=[]
        self.entry.runtime_data=self.coordinator
        await sensor.async_setup_entry(self.hass,self.entry,lambda values:created.extend(values))
        important=[e for e in created if e.serial==disk['serial'] and e.spec.key.startswith('raw_') and e._attr_entity_registry_enabled_default]
        self.assertEqual(len(important),len(smart.IMPORTANT_IDS))
        self.assertIn('Reallocated sectors',next(e for e in important if e.spec.key=='raw_5')._attr_name)
        self.assertIsNone(records[f"test-instance_{disk['serial']}_raw_5"].disabled_by)
        self.assertEqual(records[f"test-instance_{disk['serial']}_raw_160"].disabled_by,'user')
        self.data['fresh']=False
        self.assertIsNone(model.problem(self.data,'life_warning',disk['serial']))



    async def test_collection_diagnostics_lifecycle(self):
        status=model.DRIVE_SPECS[0]; error=model.DRIVE_SPECS[1]
        self.assertEqual(status.key,'collection_status')
        self.assertEqual(error.key,'collection_error')
        serial='TEST-SERIAL-0'
        self.assertEqual(model.sensor_value(self.data,status,serial),'Complete')
        self.assertEqual(model.sensor_value(self.data,error,serial),'None reported')
        entity=sensor.StartechSensor(self.coordinator,error,serial)
        self.assertTrue(entity.available)
        self.assertTrue(entity._attr_entity_registry_enabled_default)
        disk=self.data['ssds'][0]
        # Data read error after successful IDENTIFY; pause is set on this first sample.
        disk.update(error='SMART data transport failed',smart_data_valid=False,smart_thresholds_valid=False)
        self.data['service']['smart_paused']=True
        self.assertEqual(model.sensor_value(self.data,status,serial),'Error')
        self.assertEqual(entity.native_value,'SMART data transport failed')
        self.assertTrue(entity.extra_state_attributes['identity_verified'])
        # IDENTIFY failed: still report exact last-known-port observation explicitly.
        disk.update(error='IDENTIFY transport failed; port presence unknown',identity_verified=False,serial=None)
        self.assertEqual(entity.native_value,disk['error'])
        self.assertEqual(entity.extra_state_attributes['attribution'],'last_known_port')
        self.assertFalse(entity.extra_state_attributes['identity_verified'])
        # No attribution to a replacement or ambiguous last-known drive.
        disk['serial']='REPLACEMENT'
        self.assertEqual(model.sensor_value(self.data,status,serial),'Unknown')
        disk['serial']=None
        self.data['known_ssds'].append(dict(self.data['known_ssds'][0],serial='OLDER-DRIVE'))
        self.assertEqual(model.sensor_value(self.data,status,serial),'Unknown')
        self.data['known_ssds'].pop()
        # Later RAID-only sample must not retain the error or claim no error.
        self.data['smart_requested']=False;disk.update(requested=False,error=None)
        self.assertEqual(model.sensor_value(self.data,status,serial),'Paused')
        self.assertIn('paused',entity.native_value)
        self.data['service']['smart_enabled']=False
        self.assertEqual(model.sensor_value(self.data,status,serial),'Disabled')
        self.assertIn('disabled',entity.native_value)
        self.data['query_ok']=False
        self.assertEqual(model.sensor_value(self.data,status,serial),'Unknown')
        self.data['fresh']=False
        self.assertIsNone(entity.native_value)
        self.assertFalse(entity.available)
        self.assertIsNone(entity.extra_state_attributes)

    async def test_collection_diagnostics_limits_and_other_drive(self):
        serial='TEST-SERIAL-0';disk=self.data['ssds'][0]
        error=model.DRIVE_SPECS[1]
        entity=sensor.StartechSensor(self.coordinator,error,serial)
        disk['error']='x'*300
        self.assertLessEqual(len(entity.native_value),255)
        self.assertEqual(entity.extra_state_attributes['error_message'],'x'*300)
        self.assertEqual(model.collection_details(self.data,'TEST-SERIAL-1')['status'],'Complete')
        self.coordinator.last_update_success=False
        self.assertFalse(entity.available)
        self.coordinator.last_update_success=True
        self.data['duplicate_ssd_identity']=True
        self.assertEqual(model.collection_details(self.data,serial)['status'],'Unknown')
        self.data=sample();self.coordinator.data=self.data
        self.data['ssds'][0]['smart_thresholds_valid']=False
        self.assertEqual(model.collection_details(self.data,serial)['status'],'Unknown')
        self.data['sample_time_unix']-=901
        self.assertIsNone(model.collection_details(self.data,serial))


if __name__=='__main__':unittest.main()
