# -*- coding: utf-8 -*-
#
# Copyright 2008 Optaros, Inc.
#

from trac.core import *
from trac.web.api import IRequestFilter
from trac.web.chrome import add_script, add_stylesheet,ITemplateProvider
from trac.config import ListOption
from trac.util.html import html
from trac.util.compat import sorted

class MenuManagerModule(Component):
    implements(IRequestFilter, ITemplateProvider)
    managed_menus = ListOption('menu-custom', 'managed_menus', 'mainnav,metanav', sep=',',doc=""" """)
        
    # ITemplateProvider
    def get_templates_dirs(self):
        return []
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('tracmenus',resource_filename(__name__, 'htdocs'))]
   
    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler
    def post_process_request(self, req, template, data, content_type):
        req.chrome['nav_orig'] = req.chrome['nav'].copy()
        for menu_name in self.managed_menus:
            req.chrome['nav'][menu_name] = list(self._get_menu(req, menu_name, 
                                                               req.chrome['nav_orig'].get(menu_name,[])))
        add_script(req, 'tracmenus/js/superfish.js')
        add_script(req, 'tracmenus/js/tracmenus.js')
        add_script(req, 'tracmenus/js/jquery.hoverIntent.minified.js')
        add_stylesheet(req, 'tracmenus/css/superfish.css')
        return template, data, content_type
        
    def _get_menu(self, req, menu_name, menu_orig):
        config_menu = self._get_config_menus(req, menu_name)
        tree_menu={} 
        for option in sorted(menu_orig+[{'name':key} for key in config_menu.keys()], 
                             key=lambda x:config_menu.get(x['name'],{}).get('order','0')):
            if 'visited' in tree_menu.get(option['name'],[]) or config_menu.get(option['name'],{}).get('enabled', True)==False:
                continue
            name=option['name']
            tree_menu.setdefault(name, {}).update(option.copy())
            if 'label' in option and 'label' in config_menu.get(name,[]):
                del config_menu[name]['label']
            tree_menu[name].update(config_menu.get(name,{'parent_name':'unassigned'}))
            tree_menu[name]['label']=html(tree_menu[name].setdefault('label',html.a(name)))
            tree_menu[name]['visited']=True 
            
            if '_tmp_children' in tree_menu[name]:
                tree_menu[name]['children']=html.ul()
                tree_menu[name]['label'].append(tree_menu[name]['children'])
                tree_menu[name]['children'].children.extend(tree_menu[name]['_tmp_children'])
            
            if (tree_menu[name]['parent_name']=='unassigned' and not 'unassigned' in config_menu) or tree_menu[name]['parent_name']=='top': 
                yield tree_menu[name]
                continue

            tree_menu[name]['parent']=tree_menu.setdefault(tree_menu[name]['parent_name'],{})

            child_node=html.li()
            child_node.children=[tree_menu[name]['label']]
            if 'label' in tree_menu[name]['parent']:
                if not 'children' in tree_menu[name]['parent']:
                    tree_menu[name]['parent']['children']=html.ul()
                    tree_menu[name]['parent']['label'].append(tree_menu[name]['parent']['children'])
                tree_menu[name]['parent']['children'].append(child_node)
            else:
                tree_menu[name]['parent'].setdefault('_tmp_children',[]).append(child_node)

    def _get_config_menus(self, req, menu_name):
        new_menu_option=lambda name: dict(name=name, parent_name='top')
        menu={}
        for option, value in self.config[menu_name].options():
            item_parts = option.split('.',1)
            name, prop_name = item_parts[0], len(item_parts)>1 and item_parts[1] or 'enabled'
            menu.setdefault(name, new_menu_option(name)) 
            if prop_name=='parent':
                menu[name]['parent_name']=value
                continue
            elif prop_name=='enabled':
                value=self.config[menu_name].getbool(option, True)
            elif prop_name=='href':
                menu[name]['label']=menu[name].setdefault('label', html.a())(href=value.startswith('/') and req.href()+value or value)
            elif prop_name=='label':
                menu[name].setdefault('label', html.a())(value)
                continue
            menu[name][prop_name]=value
        return menu
