# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <pjg.github@ubergrabner.net>
# date: 2015/03/20
# copy: (C) Copyright 2015-EOT Canary Health, Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import six
from pyramid.request import Request
from aadict import aadict

from .decoder import Decoder, SmartSort
from .mapper import Mapper
from .engine import Engine

#------------------------------------------------------------------------------
def _extend(klass, base, spec):
  if spec is None:
    if base:
      return base
    return klass()
  if isinstance(spec, klass):
    return spec
  if base:
    return base.extend(spec)
  return klass().extend(spec)


#------------------------------------------------------------------------------
class Paginator(object):

  DEFAULTS = dict(
    page_name        = 'page',          # the pagination parameters namespace
    offset_name      = 'offset',        # the `offset` parameter name
    offset_default   = 0,               # the `offset` parameter name
    limit_name       = 'limit',         # the `limit` parameter name
    limit_default    = 25,              # the `limit` default value
    sort_name        = 'sort',          # the `sort` parameter name
    sort_default     = SmartSort,       # the `sort` default value
    count_name       = 'count',         # the `count` response parameter name
    attribute_name   = 'attribute',     # the `attribute` response parameter name
    result_name      = 'result',        # the `result` response namespace
    request_name     = 'pagination',    # the pyramid request attribute name for pagination
  )

  #----------------------------------------------------------------------------
  def __init__(self,
               decoder   = None,  # extract pagination parameters
               mapper    = None,  # what to paginate
               engine    = None,  # apply sorting & paging
               *args, **kw):
    for key, defval in Paginator.DEFAULTS.items():
      if key in kw:
        setattr(self, key, kw.pop(key))
      else:
        setattr(self, key, defval)
    self.decoder  = _extend(Decoder, None, decoder)
    self.mapper   = _extend(Mapper,  None, mapper)
    self.engine   = _extend(Engine,  None, engine)
    self.schema   = None  # used by :class:`Decoder`
    if 'comparers' in kw:
      self.engine   = self.engine.extend(comparers=kw.pop('comparers'))
    super(Paginator, self).__init__(*args, **kw)

  #----------------------------------------------------------------------------
  def extend(self, **kw):
    kw['decoder'] = _extend(Decoder, self.decoder, kw.pop('decoder', None))
    kw['mapper']  = _extend(Mapper,  self.mapper,  kw.pop('mapper',  None))
    kw['engine']  = _extend(Engine,  self.engine,  kw.pop('engine',  None))
    for key, defval in Paginator.DEFAULTS.items():
      if key not in kw:
        if getattr(self, key, None) != defval:
          kw[key] = getattr(self, key, None)
    return self.__class__(**kw)

  #----------------------------------------------------------------------------
  def __call__(self, *args, **kw):
    if len(args) != 1 or kw or not six.callable(args[0]):
      # `@paginate` was called with arguments -- force-standardize
      # todo: the problem with this implementation is that it cannot
      #       detect if you passed a function as an argument, eg.:
      #         @paginate(lambda x: foo)
      #       true, Paginate.extend() does not accept that...
      #       *and* it's not very intuitive what would be done with it...
      #       but *still* !
      #       (poor design of the python decorator API, IMHO)
      return self.extend(*args, **kw)
    func = args[0]
    def _wrapped(*args, **kw):
      return self.paginate(func, *args, **kw)
    _wrapped.__doc__ = func.__doc__
    return _wrapped

  #----------------------------------------------------------------------------
  def paginate(self, handler, *args, **kw):
    # todo: i don't particulary like this searching for the "Request"...
    request = [arg for arg in args if isinstance(arg, Request)][0]
    p8n = aadict(paginator=self, request=request)
    p8n.update(self.decoder.decode(p8n))
    setattr(request, self.request_name, p8n)
    result = handler(*args, **kw)
    value  = self.mapper.get(p8n, result)
    value  = self.engine.apply(p8n, value)
    result = self.mapper.put(p8n, result, value)
    return result

  #----------------------------------------------------------------------------
  @staticmethod
  def get_paginator(handle):
    if not callable(handle):
      return None
    if isinstance(handle, Paginator):
      return handle
    for cell in reversed(six.get_function_closure(handle) or ()):
      cell = Paginator.get_paginator(cell.cell_contents)
      if cell is not None:
        return cell
    return None


#------------------------------------------------------------------------------
paginate = Paginator()

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
