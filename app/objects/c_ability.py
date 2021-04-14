import os

import marshmallow as ma

from app.objects.interfaces.i_object import FirstClassObjectInterface
from app.objects.secondclass.c_executor import ExecutorSchema
from app.objects.secondclass.c_requirement import RequirementSchema
from app.utility.base_object import BaseObject
from app.utility.base_world import AccessSchema


class AbilitySchema(ma.Schema):
    ability_id = ma.fields.String()
    tactic = ma.fields.String(missing=None)
    technique_name = ma.fields.String(missing=None)
    technique_id = ma.fields.String(missing=None)
    name = ma.fields.String(missing=None)
    description = ma.fields.String(missing=None)
    executors = ma.fields.List(ma.fields.Nested(ExecutorSchema()))
    requirements = ma.fields.List(ma.fields.Nested(RequirementSchema()), missing=None)
    privilege = ma.fields.String(missing=None)
    repeatable = ma.fields.Bool(missing=None)
    buckets = ma.fields.List(ma.fields.String(), missing=None)
    additional_info = ma.fields.Dict(keys=ma.fields.String(), values=ma.fields.String())
    access = ma.fields.Nested(AccessSchema, missing=None)
    singleton = ma.fields.Bool(missing=None)

    @ma.post_load
    def build_ability(self, data, **_):
        return Ability(**data)


class Ability(FirstClassObjectInterface, BaseObject):

    schema = AbilitySchema()
    display_schema = AbilitySchema()

    HOOKS = dict()

    @property
    def unique(self):
        return self.ability_id

    def __init__(self, ability_id, name=None, description=None, tactic=None, technique_id=None, technique_name=None,
                 executors=None, requirements=None, privilege=None, repeatable=False, buckets=None, access=None,
                 additional_info=None, tags=None, singleton=False, **kwargs):
        super().__init__()
        self.ability_id = ability_id
        self.tactic = tactic.lower() if tactic else None
        self.technique_name = technique_name
        self.technique_id = technique_id
        self.name = name
        self.description = description
        self.executors = executors if executors else []
        self.requirements = requirements if requirements else []
        self.privilege = privilege
        self.repeatable = repeatable
        self.buckets = buckets if buckets else []
        self.singleton = singleton
        if access:
            self.access = self.Access(access)
        self.additional_info = additional_info or dict()
        self.additional_info.update(**kwargs)
        self.tags = set(tags) if tags else set()

    def __getattr__(self, item):
        try:
            return super().__getattribute__('additional_info')[item]
        except KeyError:
            raise AttributeError(item)

    def store(self, ram):
        existing = self.retrieve(ram['abilities'], self.unique)
        if not existing:
            ram['abilities'].append(self)
            return self.retrieve(ram['abilities'], self.unique)
        existing.update('tactic', self.tactic)
        existing.update('technique_name', self.technique_name)
        existing.update('technique_id', self.technique_id)
        existing.update('name', self.name)
        existing.update('description', self.description)
        existing.update('executors', self.executors)
        existing.update('privilege', self.privilege)
        return existing

    async def which_plugin(self):
        for plugin in os.listdir('plugins'):
            if await self.walk_file_path(os.path.join('plugins', plugin, 'data', ''), '%s.yml' % self.ability_id):
                return plugin
        return None

    def get_executor(self, platform, name):
        return next(iter([e for e in self.executors if e.platform == platform and e.name == name]), None)

    def get_executors(self, platform, names):
        executors = []
        for name in names:
            matched_executor = self.get_executor(platform, name)
            if matched_executor and matched_executor not in executors:
                executors.append(matched_executor)
        return executors

    def add_executor(self, executor):
        existing_executor = self.get_executor(executor.platform, executor.name)
        if existing_executor:
            self.executors.remove(existing_executor)
        self.executors.append(executor)

    async def add_bucket(self, bucket):
        if bucket not in self.buckets:
            self.buckets.append(bucket)
