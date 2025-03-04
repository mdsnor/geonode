#########################################################################
#
# Copyright (C) 2016 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################
import logging
import os.path

from io import BytesIO
from uuid import uuid4
from itertools import cycle
from taggit.models import Tag
from taggit.models import TaggedItem
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.gis.geos import Polygon
from django.core.serializers import serialize
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.core.files.uploadedfile import SimpleUploadedFile

from geonode.maps.models import Map
from geonode.base import enumerations
from geonode.layers.models import Dataset
from geonode.compat import ensure_string
from geonode.documents.models import Document
from geonode.base.models import ResourceBase, TopicCategory

# This is used to populate the database with the search fixture data. This is
# primarily used as a first step to generate the json data for the fixture using
# django's dumpdata

logger = logging.getLogger(__name__)

imgfile = BytesIO(
    b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00'
    b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)
f = SimpleUploadedFile('test_img_file.gif', imgfile.read(), 'image/gif')
dfile = [f"{settings.MEDIA_ROOT}/img.gif"]


def all_public():
    '''ensure all layers, maps and documents are publicly available'''
    for lyr in Dataset.objects.all():
        lyr.set_default_permissions()
        lyr.clear_dirty_state()
        lyr.set_processing_state(enumerations.STATE_PROCESSED)
    for mp in Map.objects.all():
        mp.set_default_permissions()
        mp.clear_dirty_state()
        mp.set_processing_state(enumerations.STATE_PROCESSED)
    for doc in Document.objects.all():
        doc.set_default_permissions()
        doc.clear_dirty_state()
        doc.set_processing_state(enumerations.STATE_PROCESSED)
    ResourceBase.objects.all().update(dirty_state=False)


def create_fixtures():
    biota = TopicCategory.objects.get(identifier='biota')
    location = TopicCategory.objects.get(identifier='location')
    elevation = TopicCategory.objects.get(identifier='elevation')
    farming = TopicCategory.objects.get(identifier='farming')
    world_extent = [-180, 180, -90, 90]

    map_data = [
        ('GeoNode Default Map', 'GeoNode default map abstract', ('populartag',), world_extent, biota),
        ('ipsum lorem', 'common ipsum lorem', ('populartag', 'maptagunique'), world_extent, biota),
        ('lorem1 ipsum1', 'common abstract1', ('populartag',), world_extent, biota),
        ('ipsum foo', 'common bar lorem', ('populartag',), world_extent, location),
        ('map one', 'common this is a unique thing', ('populartag',), [0, 1, 0, 1], location),
        ('quux', 'common double thing', ('populartag',), [0, 5, 0, 5], location),
        ('morx', 'common thing double', ('populartag',), [0, 10, 0, 10], elevation),
        ('titledupe something else ', 'whatever common', ('populartag',), [0, 10, 0, 10], elevation),
        ('something titledupe else ', 'bar common', ('populartag',), [0, 50, 0, 50], elevation),
        ('map metadata true', 'map metadata true', ('populartag',), [0, 22, 0, 22], farming),
    ]

    user_data = [
        ('bobby', 'bob', 'bobby', ''),
        ('norman', 'norman', 'norman', ''),
        ('user1', 'pass', 'uniquefirst', 'foo'),
        ('user2', 'pass', 'foo', 'uniquelast'),
        ('unique_username', 'pass', 'foo', 'uniquelast'),
        ('jblaze', 'pass', 'johnny', 'blaze'),
        ('foo', 'pass', 'bar', 'baz'),
    ]

    people_data = [
        ('this contains all my interesting profile information',),
        ('some other information goes here',),
    ]
    now = datetime.now(timezone.get_current_timezone())
    step = timedelta(days=60)

    def get_test_date():
        def it():
            current = now - step
            while True:
                yield current
                current = current - step
        itinst = it()

        def callable():
            return next(itinst)
        return callable

    next_date = get_test_date()

    dataset_data = [
        ('CA', 'abstract1', 'CA', 'geonode:CA', world_extent, next_date(), ('populartag', 'here'), elevation),
        ('layer2', 'abstract2', 'layer2', 'geonode:layer2', world_extent, next_date(), ('populartag',), elevation),
        ('uniquetitle', 'something here', 'mylayer', 'geonode:mylayer', world_extent, next_date(), ('populartag',), elevation),
        ('common blar', 'lorem ipsum', 'foo', 'geonode:foo', world_extent, next_date(), ('populartag', 'layertagunique'), location),
        ('common double it', 'whatever', 'whatever', 'geonode:whatever', [0, 1, 0, 1], next_date(), ('populartag',), location),
        ('common double time', 'else', 'fooey', 'geonode:fooey', [0, 5, 0, 5], next_date(), ('populartag',), location),
        ('common bar', 'uniqueabstract', 'quux', 'geonode:quux', [0, 10, 0, 10], next_date(), ('populartag',), biota),
        ('common morx', 'lorem ipsum', 'fleem', 'geonode:fleem', [0, 50, 0, 50], next_date(), ('populartag',), biota),
        ('dataset metadata true', 'lorem ipsum', 'fleem', 'geonode:metadatatrue', [0, 22, 0, 22], next_date(), ('populartag',), farming)
    ]

    document_data = [
        ('lorem ipsum', 'common lorem ipsum', ('populartag',), world_extent, biota),
        ('ipsum lorem', 'common ipsum lorem', ('populartag', 'doctagunique'), world_extent, biota),
        ('lorem1 ipsum1', 'common abstract1', ('populartag',), world_extent, biota),
        ('ipsum foo', 'common bar lorem', ('populartag',), world_extent, location),
        ('doc one', 'common this is a unique thing', ('populartag',), [0, 1, 0, 1], location),
        ('quux', 'common double thing', ('populartag',), [0, 5, 0, 5], location),
        ('morx', 'common thing double', ('populartag',), [0, 10, 0, 10], elevation),
        ('titledupe something else ', 'whatever common', ('populartag',), [0, 10, 0, 10], elevation),
        ('something titledupe else ', 'bar common', ('populartag',), [0, 50, 0, 50], elevation),
        ('doc metadata true', 'doc metadata true', ('populartag',), [0, 22, 0, 22], farming)
    ]

    return map_data, user_data, people_data, dataset_data, document_data


def create_models(type=None, integration=False):
    users = []
    obj_ids = []
    with transaction.atomic():
        map_data, user_data, people_data, dataset_data, document_data = create_fixtures()
        registeredmembers_group, created = Group.objects.get_or_create(name='registered-members')
        anonymous_group, created = Group.objects.get_or_create(name='anonymous')
        cont_group, created = Group.objects.get_or_create(name='contributors')
        perm = Permission.objects.get(codename='add_resourcebase')
        cont_group.permissions.add(perm)
        logger.debug("[SetUp] Get or create user admin")
        u, created = get_user_model().objects.get_or_create(username='admin')
        u.set_password('admin')
        u.is_superuser = True
        u.first_name = 'admin'
        u.save()
        u.groups.add(anonymous_group)
        users.append(u)

        for ud, pd in zip(user_data, cycle(people_data)):
            user_name, password, first_name, last_name = ud
            logger.debug(f"[SetUp] Get or create user {user_name}")
            u, created = get_user_model().objects.get_or_create(username=user_name)
            u.set_password(password)
            u.first_name = first_name
            u.last_name = last_name
            u.save()
            u.groups.add(anonymous_group)

            if not (u.is_superuser or u.is_staff or u.is_anonymous):
                u.groups.add(cont_group)
            users.append(u)

        logger.debug(f"[SetUp] Add group {anonymous_group}")
        get_user_model().objects.get(username='AnonymousUser').groups.add(anonymous_group)

        from geonode.utils import DisableDjangoSignals
        with DisableDjangoSignals(skip=integration):
            if not type or ensure_string(type) == 'map':
                for md, user in zip(map_data, cycle(users)):
                    title, abstract, kws, (bbox_x0, bbox_x1, bbox_y0, bbox_y1), category = md
                    logger.debug(f"[SetUp] Add map {title}")
                    m = Map(
                        title=title,
                        abstract=abstract,
                        zoom=4,
                        projection='EPSG:4326',
                        center_x=42,
                        center_y=-73,
                        owner=user,
                        bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
                        ll_bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
                        srid='EPSG:4326',
                        category=category,
                        metadata_only=title == 'map metadata true'
                    )
                    m.save()
                    m.set_default_permissions()
                    m.clear_dirty_state()
                    m.set_processing_state(enumerations.STATE_PROCESSED)
                    obj_ids.append(m.id)
                    for kw in kws:
                        m.keywords.add(kw)
                        m.save()

            if not type or ensure_string(type) == 'document':
                for dd, user in zip(document_data, cycle(users)):
                    title, abstract, kws, (bbox_x0, bbox_x1, bbox_y0, bbox_y1), category = dd
                    logger.debug(f"[SetUp] Add document {title}")
                    m = Document(
                        title=title,
                        abstract=abstract,
                        owner=user,
                        bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
                        ll_bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
                        srid='EPSG:4326',
                        files=dfile,
                        metadata_only=title == 'doc metadata true'
                    )
                    m.save()
                    m.set_default_permissions()
                    m.clear_dirty_state()
                    m.set_processing_state(enumerations.STATE_PROCESSED)
                    obj_ids.append(m.id)
                    for kw in kws:
                        m.keywords.add(kw)
                        m.save()

            if not type or ensure_string(type) == 'dataset':
                for ld, owner, subtype in zip(dataset_data, cycle(users), cycle(('raster', 'vector'))):
                    title, abstract, name, alternate, (bbox_x0, bbox_x1, bbox_y0, bbox_y1), start, kws, category = ld
                    end = start + timedelta(days=365)
                    logger.debug(f"[SetUp] Add dataset {title}")
                    dataset = Dataset(
                        title=title,
                        abstract=abstract,
                        name=name,
                        alternate=alternate,
                        bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
                        ll_bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
                        srid='EPSG:4326',
                        uuid=str(uuid4()),
                        owner=owner,
                        temporal_extent_start=start,
                        temporal_extent_end=end,
                        date=start,
                        subtype=subtype,
                        category=category,
                        metadata_only=title == 'dataset metadata true'
                    )
                    dataset.save()
                    dataset.set_default_permissions()
                    dataset.clear_dirty_state()
                    dataset.set_processing_state(enumerations.STATE_PROCESSED)
                    obj_ids.append(dataset.id)
                    for kw in kws:
                        dataset.keywords.add(kw)
                        dataset.save()
    return obj_ids


def remove_models(obj_ids, type=None, integration=False):
    from geonode.utils import DisableDjangoSignals
    with DisableDjangoSignals(skip=integration):
        if not type:
            remove_models(None, type=b'map')
            remove_models(None, type=b'dataset')
            remove_models(None, type=b'document')
        if type == 'map':
            try:
                m_ids = obj_ids or [mp.id for mp in Map.objects.all()]
                for id in m_ids:
                    m = Map.objects.get(pk=id)
                    m.delete()
            except Exception:
                pass
        elif type == 'dataset':
            try:
                l_ids = obj_ids or [lyr.id for lyr in Dataset.objects.all()]
                for id in l_ids:
                    dataset = Dataset.objects.get(pk=id)
                    dataset.delete()
            except Exception:
                pass
        elif type == 'document':
            try:
                d_ids = obj_ids or [doc.id for doc in Document.objects.all()]
                for id in d_ids:
                    d = Document.objects.get(pk=id)
                    d.delete()
            except Exception:
                pass


def dump_models(path=None):
    result = serialize("json", sum([list(x) for x in
                                    [get_user_model().objects.all(),
                                     Dataset.objects.all(),
                                     Map.objects.all(),
                                     Document.objects.all(),
                                     Tag.objects.all(),
                                     TaggedItem.objects.all(),
                                     ]], []), indent=2, use_natural_keys=True)
    if path is None:
        parent, _ = os.path.split(__file__)
        path = os.path.join(parent, 'fixtures', 'search_testdata.json')
    with open(path, 'w') as f:
        f.write(result)


def create_single_dataset(name):
    admin, created = get_user_model().objects.get_or_create(username='admin')
    if created:
        admin.is_superuser = True
        admin.first_name = 'admin'
        admin.set_password('admin')
        admin.save()
    test_datetime = datetime.strptime('2020-01-01', '%Y-%m-%d')
    user = get_user_model().objects.get(username='AnonymousUser')
    ll = (name, 'lorem ipsum', name, f'geonode:{name}', [
        0, 22, 0, 22], test_datetime, ('populartag',), "farming")
    title, abstract, name, alternate, (bbox_x0, bbox_x1, bbox_y0, bbox_y1), start, kws, category = ll
    dataset = Dataset(
        title=title,
        abstract=abstract,
        name=name,
        alternate=alternate,
        bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
        ll_bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
        srid='EPSG:4326',
        uuid=str(uuid4()),
        owner=user,
        temporal_extent_start=test_datetime,
        temporal_extent_end=test_datetime,
        date=start,
        subtype="vector",
        resource_type="dataset",
        typename=f"geonode:{title}"
    )
    dataset.save()
    dataset.set_default_permissions()
    dataset.clear_dirty_state()
    dataset.set_processing_state(enumerations.STATE_PROCESSED)
    return dataset


def create_single_map(name):
    admin, created = get_user_model().objects.get_or_create(username='admin')
    if created:
        admin.is_superuser = True
        admin.first_name = 'admin'
        admin.set_password('admin')
        admin.save()
    test_datetime = datetime.strptime('2020-01-01', '%Y-%m-%d')
    user = get_user_model().objects.get(username='AnonymousUser')
    ll = (name, 'lorem ipsum', name, f'{name}', [
        0, 22, 0, 22], test_datetime, ('populartag',))
    title, abstract, name, alternate, (bbox_x0, bbox_x1, bbox_y0, bbox_y1), start, kws = ll
    m = Map(
        title=title,
        abstract=abstract,
        zoom=4,
        projection='EPSG:4326',
        center_x=42,
        center_y=-73,
        owner=user,
        bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
        ll_bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
        srid='EPSG:4326',
        resource_type="map"
    )
    m.save()
    m.set_default_permissions()
    m.clear_dirty_state()
    m.set_processing_state(enumerations.STATE_PROCESSED)
    return m


def create_single_doc(name):
    admin, created = get_user_model().objects.get_or_create(username='admin')
    if created:
        admin.is_superuser = True
        admin.first_name = 'admin'
        admin.set_password('admin')
        admin.save()
    test_datetime = datetime.strptime('2020-01-01', '%Y-%m-%d')
    user = get_user_model().objects.get(username='AnonymousUser')
    dd = (name, 'lorem ipsum', name, f'{name}', [
        0, 22, 0, 22], test_datetime, ('populartag',))
    title, abstract, name, alternate, (bbox_x0, bbox_x1, bbox_y0, bbox_y1), start, kws = dd
    logger.debug(f"[SetUp] Add document {title}")
    m = Document(
        title=title,
        abstract=abstract,
        owner=user,
        bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
        ll_bbox_polygon=Polygon.from_bbox((bbox_x0, bbox_y0, bbox_x1, bbox_y1)),
        srid='EPSG:4326',
        files=dfile,
        resource_type="document"
    )
    m.save()
    m.set_default_permissions()
    m.clear_dirty_state()
    m.set_processing_state(enumerations.STATE_PROCESSED)
    return m


if __name__ == '__main__':
    create_models()
    dump_models()
