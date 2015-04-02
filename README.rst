==================
Pyramid Pagination
==================

Easy pagination for Pyramid applications! It currently has built-in support
for paginating:

* Iterable types (lists, tuples)
* SQLAlchemy Query objects

But can support pagination over any data type via extensions.


Project
=======

* Homepage: https://github.com/canaryhealth/pyramid_pagination
* Bugs: https://github.com/canaryhealth/pyramid_pagination/issues
* Manual: https://github.com/canaryhealth/pyramid_pagination/blob/master/doc/manual.rst


TL;DR
=====

Install with:

.. code-block:: bash

  $ pip install pyramid_pagination

Use default pagination with:

.. code-block:: python

  from pyramid_pagination import paginate

  @paginate
  def view(request): return range(30)

Then a request without parameters results in:

.. code-block:: json

  {
    "result": [0, 1, 2, ... , 22, 23, 24],
    "page": {
      "offset": 0,
      "limit": 25,
      "count": 30,
      "attribute": "result"
    }
  }

Paginating with some defaults changed and adding some attribute-based
sort methods:

.. code-block:: python

  from pyramid_pagination import paginate

  @paginate(limit_default=2, comparers=['name', 'value'])
  def view(request):
    return [
      dict(name='alph', value=1),
      dict(name='beta', value=2),
      dict(name='zeta', value=3),
      dict(name='alph', value=4),
    ]

Then a request with parameters
``?page.offset=1&page.limit=3&page.sort=name-,value`` results in:

.. code-block:: json

  {
    "result": [
      {"name": "beta", "value": 2},
      {"name": "alph", "value": 1},
      {"name": "alph", "value": 4}
    ],
    "page": {
      "offset": 1,
      "limit": 3,
      "count": 4,
      "sort": "name-,value",
      "attribute": "result"
    }
  }
