# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <phil@canary.md>
# date: 2015/04/02
# copy: (C) Copyright 2015-EOT Canary Health, Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import formencode
from formencode import validators
import morph

#------------------------------------------------------------------------------
class _SmartSort(object):
  MARK = '*'
  def __iter__(self):
    yield (SmartSort, True)
SmartSort = _SmartSort()

#------------------------------------------------------------------------------
class RenameFields(formencode.validators.FormValidator):
  def __init__(self, name_map, *args, **kw):
    formencode.validators.FormValidator.__init__(
      self, name_map=name_map, *args, **kw)
  def _to_python(self, value, state):
    return self.keymap(value, self.name_map)
  def _from_python(self, value, state):
    return self.keymap(value, {v: k for k, v in self.nmap})
  def keymap(self, value, nmap):
    return {nmap[k] if k in nmap else k: v for k, v in value.items()}


#------------------------------------------------------------------------------
class SortValidator(formencode.validators.FancyValidator):
  messages = {
    'bad_type'   : 'Please specify a string or list of strings',
    'bad_method' : 'Invalid sorting method "%(method)s"',
    'bad_decode' : ( 'sort specification must be a string,'
                     ' list of strings, '
                     ' or list of (string, bool) tuples' ),
  }
  def _to_python(self, value, state):
    try:
      return self.decode(value)
    except:
      raise formencode.api.Invalid(
        self.message('bad_type', state), value, state)
  @staticmethod
  def decode(spec):
    if spec is None:
      return ()
    if spec is SmartSort:
      return SmartSort
    if morph.isstr(spec):
      if spec.strip() == '':
        return ()
      if spec.strip() == SmartSort.MARK:
        return SmartSort
      spec = spec.split(',')
    if not morph.isseq(spec):
      raise ValueError(SortValidator.messages['bad_decode'])
    ret = []
    for val in spec:
      if morph.isstr(val):
        val = val.strip()
        ret.append(
          (val[:-1].strip(), False) if val.endswith('-') else (val, True))
        continue
      if len(val) == 2 \
          and morph.isstr(val[0]) \
          and val[1] in (True, False):
        ret.append(val)
        continue
      raise ValueError(SortValidator.messages['bad_decode'])
    return ret
  @staticmethod
  def encode(sort):
    if sort is SmartSort:
      return SmartSort.MARK
    if len(sort) == 0:
      return ''
    return ','.join([
      spec[0] + ( '' if spec[1] else '-' )
      for spec in sort
      if spec[0]])


#------------------------------------------------------------------------------
class Decoder(object):
  '''
  The `Decoder` translates a request into a set of query parameters
  that can be understood by the Paginator.
  '''

  #----------------------------------------------------------------------------
  def __init__(self, request_param='params', structured=False, *args, **kw):
    super(Decoder, self).__init__(*args, **kw)
    self.structured = structured
    self.params     = request_param

  #----------------------------------------------------------------------------
  def extend(self, *args, **kw):
    params = dict(structured=self.structured, request_param=self.params)
    for arg in args:
      params.update(arg)
    params.update(kw)
    return self.__class__(**params)

  #----------------------------------------------------------------------------
  def decode(self, p8n):
    if not getattr(p8n.paginator, 'schema', None):
      p8n.paginator.schema = self.make_schema(p8n)
    ret = p8n.paginator.schema.to_python(
      dict(getattr(p8n.request, self.params)))
    if p8n.paginator.page_name is not None and self.structured:
      ret = ret.get('page')
    return self.validate_sort(p8n, ret)

  #----------------------------------------------------------------------------
  def validate_sort(self, p8n, result):
    if result['sort'] is SmartSort:
      return result
    for spec in result['sort']:
      if spec[0] not in p8n.paginator.engine.comparers:
        self.invalid_sort(p8n, result, spec[0])
    return result

  #----------------------------------------------------------------------------
  def invalid_sort(self, p8n, result, method):
    val = result['sort']
    msg = SortValidator().message('bad_method', None, method=method)
    err = dict([(self.param_name(p8n, p8n.paginator.sort_name), msg)])
    exc = formencode.api.Invalid(
      '\n'.join([k + ': ' + v for k, v in err.items()]),
      val, None, error_dict=err)
    if p8n.paginator.page_name is None or not self.structured:
      raise exc
    raise formencode.api.Invalid(
      self.param_name(p8n, p8n.paginator.page_name) + ': ' + exc.msg,
      val, None, error_dict=dict([
        (self.param_name(p8n, p8n.paginator.page_name), exc)]))

  #----------------------------------------------------------------------------
  def param_name(self, p8n, param):
    if p8n.paginator.page_name is None or self.structured:
      return param
    return '.'.join([p8n.paginator.page_name, param])

  #----------------------------------------------------------------------------
  def make_schema(self, p8n):
    decoder = self
    class PaginationSchema(formencode.Schema):
      filter_extra_fields = True
      allow_extra_fields = True
      chained_validators = [
        RenameFields(dict((
          (decoder.param_name(p8n, p8n.paginator.offset_name), 'offset'),
          (decoder.param_name(p8n, p8n.paginator.limit_name),  'limit'),
          (decoder.param_name(p8n, p8n.paginator.sort_name),   'sort'),
        )))]
      def __init__(self, *args, **kw):
        super(PaginationSchema, self).__init__(*args, **kw)
        self.add_field(
          decoder.param_name(p8n, p8n.paginator.offset_name),
          validators.Int(
            min        = 0,
            if_missing = p8n.paginator.offset_default,
            if_empty   = p8n.paginator.offset_default))
        self.add_field(
          decoder.param_name(p8n, p8n.paginator.limit_name),
          validators.Int(
            min        = 0,
            if_missing = p8n.paginator.limit_default,
            if_empty   = p8n.paginator.limit_default))
        self.add_field(
          decoder.param_name(p8n, p8n.paginator.sort_name),
          SortValidator(
            if_missing = SortValidator.decode(p8n.paginator.sort_default),
            if_empty   = SortValidator.decode('')))
    schema = PaginationSchema()
    if p8n.paginator.page_name is not None and self.structured:
      subschema = PaginationSchema(if_missing=None)
      class PaginationNamespaceSchema(formencode.Schema):
        filter_extra_fields = True
        allow_extra_fields = True
        chained_validators = [
          RenameFields(dict((
            (decoder.param_name(p8n, p8n.paginator.page_name), 'page'),
          )))]
        def __init__(self, *args, **kw):
          super(PaginationNamespaceSchema, self).__init__(*args, **kw)
          self.add_field(p8n.paginator.page_name, subschema)
        def to_python(self, value):
          # todo: there *must* be a more formencode'ish way of doing this...
          ret = super(PaginationNamespaceSchema, self).to_python(value)
          if ret.get('page', None) is None:
            ret['page'] = subschema.to_python({})
          return ret
      schema = PaginationNamespaceSchema()
    return schema

#------------------------------------------------------------------------------
# end of $Id$
#------------------------------------------------------------------------------
