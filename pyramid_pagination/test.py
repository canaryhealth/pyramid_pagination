# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <pjg.github@ubergrabner.net>
# date: 2015/03/28
# copy: (C) Copyright 2015-EOT Canary Health, Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import unittest
from aadict import aadict
import morph
from pyramid.request import Request
from six.moves.urllib.parse import urlencode

#------------------------------------------------------------------------------
class TestListPagination(unittest.TestCase):

  maxDiff = None

  #----------------------------------------------------------------------------
  @staticmethod
  def request(url='/', **kw):
    # TODO: *much* better would be to override request.params... but it
    #       won't allow that! ugh. if that is fixed, go through and removed
    #       most of:
    #       - decoder={'request_param': 'data'}
    #       - param='data'
    #       - `peepsd` and `n10d`
    data = None
    if kw:
      for k, v in kw.items():
        if not morph.isstr(v) or not morph.isstr(k):
          data = kw
          break
      if data is None:
        if '?' not in url:
          url += '?'
        url += urlencode(kw)
    ret = Request.blank(url)
    if data is not None:
      ret.data = data
    return ret

  #----------------------------------------------------------------------------
  def test_invalid_sort_value(self):
    from .paginator import paginate
    import formencode.api
    @paginate(decoder={'request_param': 'data'})
    def n30(request):
      return list(range(30))
    with self.assertRaises(formencode.api.Invalid) as cm:
      n30(self.request(**{'page.sort': 88}))
    self.assertEqual(
      str(cm.exception),
      'page.sort: Please specify a string or list of strings')

  #----------------------------------------------------------------------------
  def test_invalid_sort_method(self):
    from .paginator import paginate
    import formencode.api
    @paginate
    def n30(request):
      return list(range(30))
    with self.assertRaises(formencode.api.Invalid) as cm:
      n30(self.request(**{'page.sort': 'no-such-method'}))
    self.assertEqual(
      str(cm.exception),
      'page.sort: Invalid sorting method "no-such-method"')

  #----------------------------------------------------------------------------
  def test_invalid_sort_method_structured(self):
    from .paginator import paginate
    import formencode.api
    @paginate(decoder={'structured': True, 'request_param': 'data'})
    def n30(request):
      return list(range(30))
    with self.assertRaises(formencode.api.Invalid) as cm:
      n30(self.request(page=dict(sort='no-such-method')))
    self.assertEqual(
      str(cm.exception),
      'page: sort: Invalid sorting method "no-such-method"')

  #----------------------------------------------------------------------------
  def test_decoder_structured(self):
    from .paginator import paginate
    @paginate(decoder={'structured': True, 'request_param': 'data'})
    def n30(request):
      return list(range(30))
    self.assertEqual(
      n30(self.request(page=dict(limit=10))),
      dict(
        result = list(range(10)),
        page   = dict(offset=0, limit=10, count=30, attribute='result')))

  #----------------------------------------------------------------------------
  def test_list_default(self):
    from .paginator import paginate
    @paginate
    def n30(request):
      return list(range(30))
    self.assertEqual(
      n30(self.request()),
      dict(
        result = list(range(25)),
        page   = dict(offset=0, limit=25, count=30, attribute='result')))

  #----------------------------------------------------------------------------
  def test_list_default_structured(self):
    from .paginator import paginate
    @paginate(decoder={'structured': True})
    def n30(request):
      return list(range(30))
    self.assertEqual(
      n30(self.request()),
      dict(
        result = list(range(25)),
        page   = dict(offset=0, limit=25, count=30, attribute='result')))

  #----------------------------------------------------------------------------
  def test_list_offset(self):
    from .paginator import paginate
    @paginate
    def n30(request):
      return list(range(30))
    self.assertEqual(
      n30(self.request(**{'page.offset': '10'})),
      dict(
        result = list(range(10, 30)),
        page   = dict(offset=10, limit=25, count=30, attribute='result')))

  #----------------------------------------------------------------------------
  def test_list_offsetlimit(self):
    from .paginator import paginate
    @paginate
    def n30(request):
      return list(range(30))
    self.assertEqual(
      n30(self.request(**{'page.offset': '10', 'page.limit': '5'})),
      dict(
        result = list(range(10, 15)),
        page   = dict(offset=10, limit=5, count=30, attribute='result')))

  #----------------------------------------------------------------------------
  def test_list_limit_default(self):
    from .paginator import paginate
    @paginate(limit_default=20)
    def n30(request):
      return list(range(30))
    self.assertEqual(
      n30(self.request()),
      dict(
        result = list(range(20)),
        page   = dict(offset=0, limit=20, count=30, attribute='result')))

  #----------------------------------------------------------------------------
  def test_list_limit_none(self):
    from .paginator import paginate
    @paginate(limit_default=20, decoder={'request_param': 'data'})
    def n300(request):
      return list(range(300))
    self.assertEqual(
      n300(self.request(**{'page.limit': 0})),
      dict(
        result = list(range(300)),
        page   = dict(offset=0, limit=0, count=300, attribute='result')))

  #----------------------------------------------------------------------------
  def test_list_limit_param(self):
    from .paginator import paginate
    @paginate(limit_default=20, decoder={'request_param': 'data'})
    def n30(request):
      return list(range(30))
    self.assertEqual(
      n30(self.request(**{'page.limit': 10})),
      dict(
        result = list(range(10)),
        page   = dict(offset=0, limit=10, count=30, attribute='result')))

  #----------------------------------------------------------------------------
  def test_list_sort_comparers(self):
    from .paginator import paginate
    def sort_by_evenodd(p8n, result, a, b):
      if ( a % 2 ) == ( b % 2 ):
        return 0
      if a % 2 == 0:
        return -1
      return 1
    @paginate(comparers={'evenodd': sort_by_evenodd, 'num': cmp})
    def n10(request):
      return list(range(10))
    @paginate(comparers={'evenodd': sort_by_evenodd, 'num': cmp}, decoder={'request_param': 'data'})
    def n10d(request):
      return list(range(10))
    self.assertEqual(
      n10(self.request(**{'page.sort': 'evenodd'})),
      dict(
        result = [0, 2, 4, 6, 8, 1, 3, 5, 7, 9],
        page   = dict(offset=0, limit=25, count=10, sort='evenodd', attribute='result')))
    self.assertEqual(
      n10d(self.request(**{'page.sort': 'evenodd', 'page.limit': 6})),
      dict(
        result = [0, 2, 4, 6, 8, 1],
        page   = dict(offset=0, limit=6, count=10, sort='evenodd', attribute='result')))
    self.assertEqual(
      n10(self.request(**{'page.sort': 'evenodd-'})),
      dict(
        result = [1, 3, 5, 7, 9, 0, 2, 4, 6, 8],
        page   = dict(offset=0, limit=25, count=10, sort='evenodd-', attribute='result')))
    self.assertEqual(
      n10(self.request(**{'page.sort': 'evenodd-,num'})),
      dict(
        result = [1, 3, 5, 7, 9, 0, 2, 4, 6, 8],
        page   = dict(offset=0, limit=25, count=10, sort='evenodd-,num', attribute='result')))
    self.assertEqual(
      n10(self.request(**{'page.sort': 'evenodd-,num-'})),
      dict(
        result = [9, 7, 5, 3, 1, 8, 6, 4, 2, 0],
        page   = dict(offset=0, limit=25, count=10, sort='evenodd-,num-', attribute='result')))

  #----------------------------------------------------------------------------
  def test_list_sort_default(self):
    from .paginator import paginate
    def sort_by_evenodd(p8n, result, a, b):
      if ( a % 2 ) == ( b % 2 ):
        return 0
      if a % 2 == 0:
        return -1
      return 1
    @paginate(comparers=(('evenodd', sort_by_evenodd), ('num', cmp)))
    def n10(request):
      return [3, 7, 1, 8, 0, 4, 6, 9, 2, 5]
    self.assertEqual(
      n10(self.request()),
      dict(
        result = [0, 2, 4, 6, 8, 1, 3, 5, 7, 9],
        page   = dict(offset=0, limit=25, count=10, attribute='result')))
    @paginate(comparers=(('num', cmp), ('evenodd', sort_by_evenodd)))
    def n10(request):
      return [3, 7, 1, 8, 0, 4, 6, 9, 2, 5]
    self.assertEqual(
      n10(self.request()),
      dict(
        result = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        page   = dict(offset=0, limit=25, count=10, attribute='result')))
    @paginate(sort_default='', comparers=(('num', cmp), ('evenodd', sort_by_evenodd)))
    def n10r(request):
      return [3, 7, 1, 8, 0, 4, 6, 9, 2, 5]
    self.assertEqual(
      n10r(self.request()),
      dict(
        result = [3, 7, 1, 8, 0, 4, 6, 9, 2, 5],
        page   = dict(offset=0, limit=25, count=10, attribute='result')))
    @paginate(comparers=(('num', cmp), ('evenodd', sort_by_evenodd)))
    def n10(request):
      return [3, 7, 1, 8, 0, 4, 6, 9, 2, 5]
    self.assertEqual(
      n10(self.request(**{'page.sort': ''})),
      dict(
        result = [3, 7, 1, 8, 0, 4, 6, 9, 2, 5],
        page   = dict(offset=0, limit=25, count=10, sort='', attribute='result')))

  #----------------------------------------------------------------------------
  def test_list_sort_override_default(self):
    from .paginator import paginate
    def sort_by_evenodd(p8n, result, a, b):
      if ( a % 2 ) == ( b % 2 ):
        return 0
      if a % 2 == 0:
        return -1
      return 1
    @paginate(sort_default='evenodd-,num-', comparers={'evenodd': sort_by_evenodd, 'num': cmp})
    def n10(request):
      return list(range(10))
    self.assertEqual(
      n10(self.request()),
      dict(
        result = [9, 7, 5, 3, 1, 8, 6, 4, 2, 0],
        page   = dict(offset=0, limit=25, count=10, attribute='result')))

  #----------------------------------------------------------------------------
  def test_paginate_extend(self):
    from .paginator import paginate
    paginate = paginate(limit_default=20)
    @paginate
    def n30(request):
      return list(range(30))
    self.assertEqual(
      n30(self.request()),
      dict(
        result = list(range(20)),
        page   = dict(offset=0, limit=20, count=30, attribute='result')))
    paginate = paginate(limit_default=15)
    @paginate
    def n30(request):
      return list(range(30))
    self.assertEqual(
      n30(self.request()),
      dict(
        result = list(range(15)),
        page   = dict(offset=0, limit=15, count=30, attribute='result')))
    @paginate(limit_default=10)
    def n30_10(request):
      return list(range(30))
    self.assertEqual(
      n30_10(self.request()),
      dict(
        result = list(range(10)),
        page   = dict(offset=0, limit=10, count=30, attribute='result')))
    self.assertEqual(
      n30(self.request()),
      dict(
        result = list(range(15)),
        page   = dict(offset=0, limit=15, count=30, attribute='result')))

  #----------------------------------------------------------------------------
  def test_sort_attribute_name_map(self):
    from .paginator import paginate
    paginate = paginate(sort_default='name,age-', comparers={'name': 'name', 'age': 'age'})
    @paginate
    def peeps(request):
      return [
        aadict(id=1, name='zeta', age=8),
        aadict(id=2, name='delt', age=2),
        aadict(id=3, name='zeta', age=4),
        aadict(id=4, name='acrn', age=6),
      ]
    self.assertEqual(
      peeps(self.request()),
      dict(
        result = [
          aadict(id=4, name='acrn', age=6),
          aadict(id=2, name='delt', age=2),
          aadict(id=1, name='zeta', age=8),
          aadict(id=3, name='zeta', age=4),
        ],
        page   = dict(offset=0, limit=25, count=4, attribute='result')))
    @paginate(sort_default='name,age')
    def peeps(request):
      return [
        aadict(id=1, name='zeta', age=8),
        aadict(id=2, name='delt', age=2),
        aadict(id=3, name='zeta', age=4),
        aadict(id=4, name='acrn', age=6),
      ]
    self.assertEqual(
      peeps(self.request()),
      dict(
        result = [
          aadict(id=4, name='acrn', age=6),
          aadict(id=2, name='delt', age=2),
          aadict(id=3, name='zeta', age=4),
          aadict(id=1, name='zeta', age=8),
        ],
        page   = dict(offset=0, limit=25, count=4, attribute='result')))

  #----------------------------------------------------------------------------
  def test_sort_attribute_name_list(self):
    from .paginator import paginate
    paginate = paginate(sort_default='name,age-', comparers=['name', 'age'])
    @paginate
    def peeps(request):
      return [
        aadict(id=1, name='zeta', age=8),
        aadict(id=2, name='delt', age=2),
        aadict(id=3, name='zeta', age=4),
        aadict(id=4, name='acrn', age=6),
      ]
    self.assertEqual(
      peeps(self.request()),
      dict(
        result = [
          aadict(id=4, name='acrn', age=6),
          aadict(id=2, name='delt', age=2),
          aadict(id=1, name='zeta', age=8),
          aadict(id=3, name='zeta', age=4),
        ],
        page   = dict(offset=0, limit=25, count=4, attribute='result')))


#------------------------------------------------------------------------------
class TestSqlalchemyPagination(unittest.TestCase):

  maxDiff = None

  #----------------------------------------------------------------------------
  @staticmethod
  def request(*args, **kw):
    return TestListPagination.request(*args, **kw)

  #----------------------------------------------------------------------------
  def makedb(self):
    import sqlalchemy as sa
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    engine = sa.create_engine('sqlite://')
    Base = declarative_base()
    class Person(Base):
      __tablename__ = 'persons'
      id = sa.Column(sa.Integer, primary_key=True)
      name = sa.Column(sa.String)
      age = sa.Column(sa.Integer)
    class User(Base):
      __tablename__ = 'users'
      id = sa.Column(sa.Integer, primary_key=True)
      person_id = sa.Column(sa.Integer)
    Base.metadata.create_all(engine) 
    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    model = aadict(engine=engine, Person=Person, User=User, session=session)
    return model

  #----------------------------------------------------------------------------
  def populate(self, model):
    model.session.add(model.Person(id=1, name='zeta', age=8))
    model.session.add(model.Person(id=2, name='delt', age=2))
    model.session.add(model.Person(id=3, name='zeta', age=4))
    model.session.add(model.Person(id=4, name='acrn', age=6))
    model.session.add(model.User(id=4, person_id=1))
    model.session.add(model.User(id=5, person_id=2))
    model.session.add(model.User(id=3, person_id=3))
    model.session.add(model.User(id=6, person_id=4))
    model.session.commit()
    return model

  #----------------------------------------------------------------------------
  def query(self, model, request, param='params'):
    ret = model.session.query(model.Person)
    if 'minage' in getattr(request, param):
      ret = ret.filter(
        model.Person.age >= int(getattr(request, param).get('minage')))
    return ret

  #----------------------------------------------------------------------------
  def dictify(self, result, pick=('id', 'name', 'age'), pluck=None):
    if pick:
      result['result'] = [morph.pick(peep, *pick) for peep in result['result']]
    if pluck:
      result['result'] = [peep[pluck] for peep in result['result']]
    return result

  #----------------------------------------------------------------------------
  def test_sqlalchemy(self):
    model = self.populate(self.makedb())
    from .paginator import paginate
    @paginate
    def peeps(request):
      return self.query(model, request)
    @paginate(decoder={'request_param': 'data'})
    def peepsd(request):
      return self.query(model, request, param='data')
    self.assertEqual(
      self.dictify(peeps(self.request()), pluck='name'),
      dict(
        page   = dict(offset=0, limit=25, count=4, attribute='result'),
        result = ['zeta', 'delt', 'zeta', 'acrn']))
    self.assertEqual(
      self.dictify(peepsd(self.request(minage=6)), pluck='id'),
      dict(
        page   = dict(offset=0, limit=25, count=2, attribute='result'),
        result = [1, 4]))

  #----------------------------------------------------------------------------
  def test_sqlalchemy_limit(self):
    model = self.populate(self.makedb())
    from .paginator import paginate
    @paginate(decoder={'request_param': 'data'})
    def peeps(request):
      return self.query(model, request)
    self.assertEqual(
      self.dictify(peeps(self.request(**{'page.limit': 2})), pluck='id'),
      dict(
        page   = dict(offset=0, limit=2, count=4, attribute='result'),
        result = [1, 2]))

  #----------------------------------------------------------------------------
  def test_sqlalchemy_offset(self):
    model = self.populate(self.makedb())
    from .paginator import paginate
    @paginate(decoder={'request_param': 'data'})
    def peeps(request):
      return self.query(model, request)
    self.assertEqual(
      self.dictify(peeps(self.request(**{'page.offset': 1})), pluck='id'),
      dict(
        page   = dict(offset=1, limit=25, count=4, attribute='result'),
        result = [2, 3, 4]))

  #----------------------------------------------------------------------------
  def test_sqlalchemy_offsetlimit(self):
    model = self.populate(self.makedb())
    from .paginator import paginate
    @paginate(decoder={'request_param': 'data'})
    def peeps(request):
      return self.query(model, request)
    self.assertEqual(
      self.dictify(peeps(self.request(**{'page.offset': 1, 'page.limit': 1})), pluck='id'),
      dict(
        page   = dict(offset=1, limit=1, count=4, attribute='result'),
        result = [2]))

  #----------------------------------------------------------------------------
  def test_sqlalchemy_sort(self):
    model = self.populate(self.makedb())
    from .paginator import paginate
    @paginate(sort_default='name', comparers={'name': 'name', 'age': 'age'})
    def peeps(request):
      return self.query(model, request)
    self.assertEqual(
      self.dictify(peeps(self.request()), pluck='name'),
      dict(
        page   = dict(offset=0, limit=25, count=4, attribute='result'),
        result = ['acrn', 'delt', 'zeta', 'zeta']))
    self.assertEqual(
      self.dictify(peeps(self.request(**{'page.sort': 'name-'})), pluck='name'),
      dict(
        page   = dict(offset=0, limit=25, count=4, sort='name-', attribute='result'),
        result = ['zeta', 'zeta', 'delt', 'acrn']))
    self.assertEqual(
      self.dictify(peeps(self.request(**{'page.sort': 'age'})), pluck='id'),
      dict(
        page   = dict(offset=0, limit=25, count=4, sort='age', attribute='result'),
        result = [2, 3, 4, 1]))
    self.assertEqual(
      self.dictify(peeps(self.request(**{'page.sort': 'age-'})), pluck='id'),
      dict(
        page   = dict(offset=0, limit=25, count=4, sort='age-', attribute='result'),
        result = [1, 4, 3, 2]))
    self.assertEqual(
      self.dictify(peeps(self.request(**{'page.sort': 'name,age'})), pluck='id'),
      dict(
        page   = dict(offset=0, limit=25, count=4, sort='name,age', attribute='result'),
        result = [4, 2, 3, 1]))
    self.assertEqual(
      self.dictify(peeps(self.request(**{'page.sort': 'name,age-'})), pluck='id'),
      dict(
        page   = dict(offset=0, limit=25, count=4, sort='name,age-', attribute='result'),
        result = [4, 2, 1, 3]))

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
