=========================
Pyramid Pagination Manual
=========================


Overview
========

The ``pyramid_pagination`` package brings easy pagination to Pyramid
view handlers via function/method decoration. It currently has
built-in support for paginating:

* Iterable types (lists, tuples)
* SQLAlchemy Query objects

But can support pagination over any data type via extensions.


Usage
=====

The main `pyramid_pagination` facility is the `paginate` decorator.
The decorator is implemented as a class that can be chain-extended by
calling it with additional parameters, which returns a new decorator.

Some examples:

.. code-block:: python

  from pyramid_pagination import paginate

  # create a paginator that uses a custom engine
  my_paginate = paginate(engine=MyCustomEngine())

  # then extend that one that defaults to 100 items per page
  big_paginate = my_paginate(limit_default=100)

  # decorate a view with defaults
  @my_paginate
  def handler(request): ...

  # decorate a view with some attribute-based sorting methods
  @big_paginate(comparers=['name', 'value'])
  def handler(request): ...

  # decorate a view with sqlalchemy sorting and descending value default sort
  @big_paginate(comparers={'value': Model.exposed_currency}, sort_default='value-')
  def handler(request): ...


Typical Usage
=============

The "typical" way to use pyramid_pagination is to create a
application-specific `paginate` decorator with your application's
default pagination approach, and then import that into the views,
handlers, and/or controllers where you need it.

Example application's ``myapp/pagination.py`` module:

.. code-block:: python

   # myapp/pagination.py

   from pyramid_pagination import paginate

   paginate = paginate(limit_default=50)

Then import this from all of the application's request handlers:

.. code-block:: python

   # myapp/handler.py

   from myapp.pagination import paginate

   @paginate(sort_default='value', comparers=['value', 'name'])
   def handler(request):
     ...


Concepts
========


Paginator
---------

This is the main pyramid_pagination object that gets used as a request
handler decorator. It is responsible for orchestrating the Decoder,
Engine, and Mapper activities to narrow a result set to the requested
page.


Decoder
-------

The pagination Decoder object interprets and validates request
parameters intended to control the Paginator behaviour.


Engine
------

The pagination Engine object does the real work: it determines which
items in a result set fit the current request parameters. The main
facets are sorting, offset, and limit. This process is referred to as
:term:`narrowing` the result set.


Mapper
------

The pagination Mapper object extracts the result set to be narrowed
from the request handler's return value. It is also responsible for
then creating the return value from the pagination.


Processing Workflow
===================

When a Paginator gets involved in the handling of a Pyramid request,
the following happens:

1. Pyramid, as usual, selects the appropriate view handler for a
   request (via URL traversal, dispatch, or controllers).

2. The `paginate` decorator is invoked, which is an instance of a
   `Paginator` class.

3. The Paginator's `Decoder` instance examines the request for
   pagination parameters and ensures their validity, and if there is
   an error, raises a `formencode.api.Invalid` exception.

4. The `Request` object is decorated with a `.pagination` attribute,
   which has a reference to the current parameters.

5. The view handler is invoked with the request and processes it,
   preparing a response result set based any other non-pagination
   related parameters in the request (i.e. the request query itself).

6. The return value of the view handler is intercepted by the
   Paginator, which uses the `Mapper` to locate the result set to be
   paginated (in the case that the return value itself is not the
   result set to be paginated).

7. The `Engine` is then given the result set and pagination
   parameters, and performs the actual sorting and pagination, the
   details of which depend on the data type of the result set.

8. The `Mapper` is then used to splice the final result set and the
   pagination meta-information back into the return value, and the
   result is returned to Pyramid.


Important Notes
===============

* It is the caller's responsibility to ensure that the result data
  type and the comparers are compatible, i.e. that a SQLAlchemy Query
  result set has comparers that can be appended via
  `Query.order_by()`.

* The default default sorting method (i.e. if neither the request nor
  the `@paginate` decoration specifies it) is to use "SmartSort",
  which cascades through *all* methods, in the comparers' defined
  order. Therefore, care must be taken to use an OrderedDict, specify
  them in order, or explicitly set the `sort_default` parameter. Some
  examples:

  .. code-block:: python

    # define default sort via list
    @paginate(comparers=(('meth1', axis_1), ('meth2', axis_2)))

    # define default sort via OrderedDict
    @paginate(comparers=collections.OrderedDict(meth1=axis_1, meth2=axis_2))

    # define default sort explicitly
    @paginate(comparers=dict(meth1=axis_1, meth2=axis_2), sort_default='meth1,meth2')

    # explicitly disable default sorting
    @paginate(comparers=dict(meth1=axis_1, meth2=axis_2), sort_default='')

    # define default sorting via attributes
    @paginate(comparers=['attr1', 'attr2', 'attr3'])


Comparers
=========

The default engine has built-in support for the following types
of paginated elements and the applicable comparator types:

* ``iterable``

  A simple list or tuple. The following comparer types are supported:

  * ``callable(A, B)``:

    A callable that takes two objects to be compared and returns their
    ordering relationship in an ascending order; i.e. must return -1
    (A comes before B), 0 (A and B are identical), or 1 (A comes after
    B). The engine takes care of reversing this if in descending mode.
    If this form is used, it must only accept exactly two parameters.

  * ``callable(pagination, result, A, B)``:

    Same as the first option, except that the pagination state and the
    unsorted result set are passed in as parameters. Note that a
    `TypeError` exception is how the engine decides between the two
    callable options, i.e. your callable should only accept exactly
    two parameters if it is the first type.

  * ``string``:

    The attribute or item key name whose value is to be used to
    compare objects using the built-in ``cmp`` function.

  Example:

  .. code-block:: python

    from pyramid_pagination import paginate

    def cmp_age(a, b):
      return (a.end - a.start) - (b.end - b.start)

    @paginate(comparers={'value': 'value', 'age': cmp_age})
    def handler(request): ...


* ``sqlalchemy.orm.Query``:

  A SQLAlchemy Query object, unevaluated. The following comparers
  are supported:

  * ``string``:

    The name of the model's attribute that can be used in an ``ORDER
    BY`` clause.

  * ``callable(pagination, query, method, ascending)``:

    A callable that decorates the `query` in some way and returns the
    new Query object. The first keyword parameter, ``pagination``, is
    the pagination state object. The third keyword parameter,
    `method`, is the name of the current sorting dimension. The fourth
    keyword parameter, `ascending`, is a bool that indicates whether
    or not the order should be ascending or descending.

  * Otherwise:

    Anything else is passed directly to `Query.order_by()`.

  Example:

  .. code-block:: python

    from pyramid_pagination import paginate

    def cmp_age(p8n, query, method, ascending):
      return query.order_by('"end" - "start"' + ( '' if ascending else ' DESC' ))

    @paginate(comparers={'value': 'value', 'age': cmp_age})
    def handler(request): ...

    # identical to (assuming `model` is an SQLAlchemy ORM model)

    @paginate(comparers={'value': 'value', 'age': ( model.end - model.start )})
    def handler(request): ...

    # and identical to (assuming `model` has an `age` hybrid_property)

    @paginate(comparers=['value', 'age'])
    def handler(request): ...


Options
=======

The `paginate` decorator supports many options to configure and extend
its functionality. These options are supported regardless of how it is
invoked, e.g. as a decorator without arguments, a decorator with
arguments, or when extending the paginator to create a new paginator.

* ``decoder`` : { dict, list, pyramid_pagination.Decoder }

  Controls how a request's pagination parameters are interpreted.
  See `Decoder Options`_ for details.

* ``mapper`` : { dict, list, pyramid_pagination.Mapper }

  Controls how the paginated elements are extracted from the handler's
  return value and how the pagination result and parameters are
  injected into the final return value. See `Mapper Options`_ for
  details.

* ``engine`` : { dict, list, pyramid_pagination.Engine }

  Controls how a result set is sorted and paginated. See `Engine
  Options`_ for details.

* ``comparers`` : { dict, list }, default: {}

  Shorthand for ``engine={'comparers': VALUE}``.

* ``page_name`` : str, default: 'page'

  The pagination parameters namespace. Can be set to null to disable
  namespacing the parameters.

* ``offset_name`` : str, default: 'offset'

  The `offset` parameter name.

* ``offset_default`` : int, default: 0

  The `offset` parameter name.

* ``limit_name`` : str, default: 'limit'

  The `limit` parameter name.

* ``limit_default`` : int, default: 25

  The `limit` default value.

* ``sort_name`` : str, default: 'sort'

  The `sort` parameter name.

* ``sort_default`` : str, default: pyramid_pagination.SmartSort

  The `sort` default value.

* ``count_name`` : str, default: 'count'

  The `count` response parameter name.

* ``attribute_name`` : str, default: 'attribute'

  The `attribute` response parameter name.

* ``result_name`` : str, default: 'result'

  The default `result` response namespace (when wrapping is needed).

* ``request_name`` : str, default: 'pagination'

  The pyramid request attribute name where the per-request pagination
  state object will be stored.

* ``map_item`` : callable, default: null

  Specifies a callback function that allows each object selected for
  the current page to be remapped in some way. The callback gets
  invoked after the result set is narrowed to the selected page. This
  function is called once for each item with the following keyword
  arguments:

  * ``state`` : the pagination state object
  * ``result`` : the initial non-paginated result
  * ``value`` : the subset of `result` selected for the current page
  * ``item`` : the current item being 
  * ``attributes`` : some of the current page attributes

  The return value should be the remapped item by itself.

* ``map_list`` : callable, default: null

  Specifies a callback function that allows the list of objects
  selected for the current page to be remapped in some way. The
  callback gets invoked after the result set is narrowed to the
  selected page and each item was passed through `map_item`. This
  function is called once per pagination request with the following
  keyword arguments:

  * ``state`` : the pagination state object
  * ``result`` : the initial non-paginated result
  * ``value`` : the subset of `result` selected for the current page
  * ``attributes`` : some of the current page attributes

  The return value should be a tuple of the ``(adjusted_value,
  adjusted_attributes)``.

* ``map_return`` : callable, default: null

  Specifies a callback function that allows the final pagination
  return value to be remapped in some way. The callback gets invoked
  after the result set is narrowed to the selected page, `map_item`
  and `map_list` are applied, and any `Mapper` injections take place.
  This function is called once per pagination request with the
  following keyword arguments:

  * ``state`` : the pagination state object
  * ``result`` : the initial non-paginated result
  * ``value`` : the current return value

  The return value should be the adjusted `value`.

* ``keep_items`` : bool, default: false

  By default, the narrowed result set (i.e. the items selected for the
  currently requested page) is not kept around as it passes through
  the mappers (such as `map_item`). If `keep_items` is enabled, the
  narrowed result set is cached in the `items` attribute of the
  pagination state object. Note that `items` is a method name of the
  state object, so it needs to be accessed via item-access,
  e.g. ``state['items']`` or ``state.get('items')``.

* ``force_list`` : bool, default: true

  The Paginator tries to operate as leanly memory-wise as possible,
  and for this reason uses generators for handling items. The final
  hand-off result to the upstream handlers can therefore include
  generators. This option (when set to true), will force the result
  set to be a tuple or list, which is necessary if upstream handlers
  can't handle generators. To be safe (and backward-compatible), this
  defaults to true.


Decoder Options
===============

When specifying options to the paginator `decoder` attribute, it can
either be a `pyramid_pagination.Decoder` subclass instance or a set of
parameters that will be passed on directly to the current decoder's
`.extend()` method. The decoder supports the following options:

* ``request_param`` : str, default: 'params'

  The name of the `pyramid.request.Request` object's attribute that
  the pagination parameters should be extracted from. By default, it
  uses the ``'params'`` attribute, which is a merge of both GET and
  POST parameters.

* ``structured`` : bool, default: false

  Whether or not the parameters stored in `request_param` are simple
  one-dimensional key/value pairs, or if they are tree-based
  structured objects. The key difference is how the page namespace is
  handled when extracting parameters. For example, assuming that all
  other parameters are left to their defaults, the page offset is
  extracted as follows:

  .. code-block:: python

    # with structured false
    offset = request.params.get('page.offset')

    # with structured true
    offset = request.params.get('page').get('offset')

Examples:

.. code-block:: python

  from pyramid_pagination import paginate, Decoder

  # using parameterized default decoder

  pager1 = paginate(decoder={'request_params': 'data', 'structured': True})

  @pager1
  def handler(request): ...

  # identical to

  @paginate(decoder={'request_params': 'data', 'structured': True})
  def handler(request): ...

  # using custom decoder

  class MyDecoder(Decoder):
    def decode(self, p8n):
      return dict(
        offset = p8n.request.GET['offset'],
        limit  = p8n.request.GET['limit'],
      )

  @paginate(decoder=MyDecoder())
  def handler(request): ...


Mapper Options
==============

When specifying options to the paginator `mapper` attribute, it can
either be a `pyramid_pagination.Mapper` subclass instance or a set of
parameters that will be passed on directly to the current mapper's
`.extend()` method. The mapper supports the following options:

* ``target`` : str, default: none

  The dotted-dictionary path to the paginated elements list within the
  result set returned by the request handler. If not specified, the

Examples:

.. code-block:: python

  from pyramid_pagination import paginate, Mapper

  # using parameterized default mapper

  pager1 = paginate(mapper={'target': 'objects.elements'})

  @pager1
  def handler(request): ...

  # identical to

  @paginate(mapper={'target': 'objects.elements'})
  def handler(request): ...

  # using custom mapper

  class MyMapper(Mapper):
    def get(self, p8n, result):
      return result['objects']['elements']
    def put(self, p8n, result, outcome):
      result['objects']['elements'] = outcome[0]
      result['page']                = outcome[1]
      return result

  @paginate(mapper=MyMapper())
  def handler(request): ...


Engine Options
==============

When specifying options to the paginator `engine` attribute, it can
either be a `pyramid_pagination.Engine` subclass instance or a set of
parameters that will be passed on directly to the current engine's
`.extend()` method. The engine supports the following options:

* ``comparers`` : { dict, list }, default: {}

  Adds to the current set of supported sorting methods. See
  `Comparers`_ for details on supported types.

Examples:

.. code-block:: python

  from pyramid_pagination import paginate, Engine

  # using parameterized default engine

  pager1 = paginate(engine={'comparers': ['key']})

  @pager1
  def handler(request): ...

  # identical to

  @paginate(engine={'comparers': ['key']})
  def handler(request): ...

  # and identical to the shorthand form

  @paginate(comparers=['key'])
  def handler(request): ...

  # using custom engine

  class MyEngine(Engine):
    def apply(self, p8n, value):
      # very dumb implementation that always returns the first two elements
      return (sorted(value)[:2], {})

  @paginate(engine=MyEngine())
  def handler(request): ...


Pagination State
================

In the implementation and the documentation, there are many references
to a "pagination state", often named ``p8n``. This pagination state is
a *per-request* object that is added to the pyramid request object
during handling and has the following parameters:

* ``paginator``:

  The currently active pagination object instance.

* ``request``:

  The currently active request.

* ``offset``:

  The pagination offset to be used for the current request.

* ``limit``:

  The pagination limit to be used for the current request.

* ``sort``:

  The pagination sort methods to be used for the current request. Note
  that this is a list of two-element tuples of ``(method, ascending)``
  where the `method` is the method name string, and `ascending` is a
  bool value.
