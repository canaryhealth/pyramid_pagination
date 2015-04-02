# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <phil@canary.md>
# date: 2015/04/02
# copy: (C) Copyright 2015-EOT Canary Health, Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import six
import morph
import sqlalchemy
import sqlalchemy.orm
from collections import OrderedDict

from .decoder import SmartSort

#------------------------------------------------------------------------------
class Engine(object):
  '''
  The `Engine` performs the actual pagination work of narrowing down
  the result set to the desired window.
  '''

  #----------------------------------------------------------------------------
  def __init__(self, comparers={}, *args, **kw):
    super(Engine, self).__init__(*args, **kw)
    self.comparers = OrderedDict()
    if morph.isseq(comparers) and len(comparers) > 0 \
        and not morph.isseq(comparers[0]):
      self.comparers.update((k, k) for k in comparers)
    else:
      self.comparers.update(comparers)

  #----------------------------------------------------------------------------
  def extend(self, *args, **kw):
    params = dict(comparers=self.comparers)
    for arg in args:
      params.update(arg)
    params.update(kw)
    return self.__class__(**params)

  #----------------------------------------------------------------------------
  def apply(self, p8n, value):
    '''
    Returns a two-element tuple of ``(narrowed_value, page_attributes)``.
    '''
    if isinstance(value, sqlalchemy.orm.Query):
      return self.apply_sqlalchemy_orm_query_query(p8n, value)
    try: value = list(value)
    except: pass
    try:
      method = getattr(self, 'apply_' + self.route(value))
    except:
      raise ValueError('No pagination available for %r' % (type(value),))
    return method(p8n, value)

  #----------------------------------------------------------------------------
  def route(self, value):
    ret = type(value)
    if ret.__module__ in ('__builtin__', 'builtin'):
      return ret.__name__.lower()
    return '.'.join([ret.__module__, ret.__name__]).lower()

  #----------------------------------------------------------------------------
  def sorters(self, p8n):
    if p8n.sort is not SmartSort:
      return p8n.sort
    return [(key, True) for key in self.comparers.keys()]

  #----------------------------------------------------------------------------
  def apply_list(self, p8n, value):
    sorters = self.sorters(p8n)
    def sortfunc(a, b):
      for meth, asc in sorters:
        spec = self.comparers[meth]
        if spec is None:
          continue
        elif six.callable(spec):
          try:
            ret = spec(p8n, value, a, b)
          except TypeError:
            ret = spec(a, b)
        elif morph.isstr(spec):
          try:
            ret = cmp(getattr(a, spec), getattr(b, spec))
          except AttributeError:
            ret = cmp(a[spec], b[spec])
        else:
          raise ValueError(
            'pagination sort comparer must be a callable,'
            ' an attribute, or an item key')
        if ret == 0:
          continue
        if asc:
          return ret
        if ret < 0:
          return 1
        return -1
      return 0
    value = sorted(value, cmp=sortfunc)
    count = len(value)
    if p8n.limit > 0:
      value = value[p8n.offset : p8n.offset + p8n.limit]
    else:
      value = value[p8n.offset : ]
    return (value, dict(count=count))

  #----------------------------------------------------------------------------
  def apply_sqlalchemy_orm_query_query(self, p8n, query):
    for meth, asc in self.sorters(p8n):
      spec = self.comparers[meth]
      if spec is None:
        continue
      elif six.callable(spec):
        query = spec(pagination=p8n, query=query, method=meth, ascending=asc)
      elif morph.isstr(spec):
        query = query.order_by(spec + ( '' if asc else ' DESC' ))
      else:
        query = query.order_by(spec if asc else sqlalchemy.desc(spec))
    count = query.count()
    query = query.offset(p8n.offset)
    if p8n.limit > 0:
      query = query.limit(p8n.limit)
    return (query, dict(count=count))

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
