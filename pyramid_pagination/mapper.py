# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <phil@canary.md>
# date: 2015/04/02
# copy: (C) Copyright 2015-EOT Canary Health, Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import morph

from .decoder import SortValidator, SmartSort

#------------------------------------------------------------------------------
class Mapper(object):
  '''
  A `Mapper` selects the result set to be paginated from the
  response and transforms the response to contain the paginated result
  set and the pagination meta-information.
  '''

  #----------------------------------------------------------------------------
  def __init__(self, target=None, *args, **kw):
    super(Mapper, self).__init__(*args, **kw)
    self.target = None

  #----------------------------------------------------------------------------
  def extend(self, *args, **kw):
    params = dict(target=self.target)
    for arg in args:
      params.update(arg)
    params.update(kw)
    return self.__class__(**params)

  #----------------------------------------------------------------------------
  def get(self, p8n, result):
    return self.resolve(p8n, result)()

  #----------------------------------------------------------------------------
  def resolve(self, p8n, result):
    '''
    Returns a function that is expected to be called in one of the
    following ways:

    * as a "getter" (with no arguments)
    * as a "setter" (with exactly one argument)
    * returns the target path (with exactly two arguments)
    '''
    # todo: this `exactly two arguments` is ridiculous... change!
    if self.target is not None:
      return self.resolve_target(p8n, result)
    if not morph.isdict(result):
      def _resolve(*args):
        if len(args) <= 0:
          return result
        if len(args) == 1:
          return dict(((p8n.paginator.result_name, args[0]),))
        if len(args) == 2:
          return p8n.paginator.result_name
      return _resolve
    if len(result.keys()) != 1:
      raise ValueError(
        'Pagination of multi-key dictionaries requires setting the'
        ' pagination mapper "target" attribute')
    key = result.keys()[0]
    def _resolve(*args):
      if len(args) <= 0:
        return result[key]
      if len(args) == 1:
        return dict([(key, args[0])])
      if len(args) == 2:
        return key
    return _resolve

  #----------------------------------------------------------------------------
  def resolve_target(self, p8n, result):
    # todo: support list-index style notation as well, eg:
    #       ``foo-1.bar`` would resolve to the ``"here"`` element in:
    #       {foo: [{bar: 'no'}, {bar: 'here'}, {bar: 'nada'}]}
    # TODO: do error checking for missing keys...
    container = result
    keys = self.target.split('.')
    for key in keys[:-1]:
      container = container.get(key)
    key = keys[-1]
    def _resolve(*args):
      if len(args) <= 0:
        return container[key]
      if len(args) == 1:
        container[key] = args[0]
        return result
      if len(args) == 2:
        return self.target
    return _resolve

  #----------------------------------------------------------------------------
  def put(self, p8n, result, value):
    result = self.put_data(p8n, result, value)
    result = self.put_meta(p8n, result, value)
    return result

  #----------------------------------------------------------------------------
  def put_data(self, p8n, result, value):
    resolver = self.resolve(p8n, result)
    value[1]['attribute'] = resolver(None, None)
    return resolver(value[0])

  #----------------------------------------------------------------------------
  def put_meta(self, p8n, result, value):
    page = dict()
    if 'count' in value[1]:
      page[p8n.paginator.count_name]  = value[1]['count']
    page[p8n.paginator.offset_name] = p8n.offset
    page[p8n.paginator.limit_name]  = p8n.limit
    sort = SortValidator.encode(p8n.sort)
    if sort != ( SmartSort.MARK
                 if p8n.paginator.sort_default is SmartSort
                 else p8n.paginator.sort_default ):
      page[p8n.paginator.sort_name] = sort
    page[p8n.paginator.attribute_name] = value[1].get(
      'attribute', p8n.paginator.result_name) or p8n.paginator.result_name
    try:
      ret = dict(result)
    except ValueError:
      # todo: what the ... ?
      ret = dict(result=result)
    ret[p8n.paginator.page_name] = page
    return ret


#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
