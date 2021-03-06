#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# Copyright 2007-2008 Optaros, Inc
#
# (c) Aleksey A. Porfirov, 2012
# Minor refactoring/enhancement
# Add 'hide_if_no_original' config prop
# Fix active items


from setuptools import setup

setup(name="TracMenusPlugin",
      version="0.1.1a",
      packages=['tracmenus'],
      author="Catalin Balan", 
      author_email="cbalan@optaros.com", 
      url="http://code.optaros.com/trac/oforge",
      description="Trac Menus",
      license="BSD",
      entry_points={'trac.plugins': [
            'tracmenus.web_ui = tracmenus.web_ui', 
            ]},
      package_data={'tracmenus' : ['htdocs/js/*.js', 
                                         'htdocs/css/*.css', 
                                         'templates/*.html',
                                         'htdocs/images/*.png']}
)
