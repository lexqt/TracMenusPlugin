# -*- coding: utf-8 -*-
#
# Copyright 2008 Optaros, Inc.
#
import re

from trac.core import *
from trac.web.api import IRequestFilter
from trac.web.chrome import add_script, add_stylesheet,ITemplateProvider
from trac.config import ListOption, BoolOption
from trac.util.html import html
from trac.util.compat import sorted

class MenuManagerModule(Component):
    implements(IRequestFilter, ITemplateProvider)
    managed_menus = ListOption('menu-custom', 'managed_menus', 'mainnav,metanav', sep=',', doc=""" """)
    serve_ui_files = BoolOption('menu-custom', 'serve_ui_files', 'true')

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
        if 'ctxtnav' in self.managed_menus and 'ctxtnav' in req.chrome:
            req.chrome['nav_orig']['ctxtnav']=[dict(name='ctxtnav_'+str(idx), label=ctx_label) 
                                               for idx, ctx_label in enumerate(req.chrome['ctxtnav'])]
        for menu_name in self.managed_menus:
            req.chrome['nav'][menu_name] = list(self._get_menu(req, menu_name, 
                                                               req.chrome['nav_orig']))
            if menu_name=='ctxtnav':
                req.chrome['ctxtnav'] = [ ctxt_item.get('label') for ctxt_item in req.chrome['nav'][menu_name] ]
                
        if self.serve_ui_files:
            add_script(req, 'tracmenus/js/superfish.js')
            add_script(req, 'tracmenus/js/tracmenus.js')
            add_script(req, 'tracmenus/js/jquery.hoverIntent.minified.js')
            add_stylesheet(req, 'tracmenus/css/superfish.css')
        return template, data, content_type
        
    def _get_menu(self, req, menu_name, nav_orig):
        config_menu, config_options = self._get_config_menus(req, menu_name)
        menu_orig = nav_orig.get(menu_name, [])
        
        if 'inherit' in config_options:
            menu_orig += nav_orig.get(config_options['inherit'], [])
            
        tree_menu={} 
        for option in sorted(menu_orig+[{'name':key} for key in config_menu.keys()], 
                             key=lambda x:config_menu.get(x['name'],{}).get('order','0')):
            if 'visited' in tree_menu.get(option['name'],[]) \
                    or config_menu.get(option['name'],{}).get('enabled', True)==False \
                    or config_menu.get(option['name'],{}).get('if_path_info', True)==False:
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
        menu, options = {}, {}
        for option, value in self.config[menu_name].options():
            item_parts = option.split('.',1)
            name, prop_name = item_parts[0], len(item_parts)>1 and item_parts[1] or 'enabled'
            if name in ['inherit']:
                options[name] = value
                continue
            menu.setdefault(name, new_menu_option(name)) 
            if prop_name=='parent':
                menu[name]['parent_name']=value
                continue
            elif prop_name=='enabled':
                value=self.config[menu_name].getbool(option, True)
            elif prop_name=='href':
                value = value.replace('$PATH_INFO', req.path_info)
                menu[name]['label']=menu[name].setdefault('label', html.a())(href=value.startswith('/') and req.href()+value or value)
            elif prop_name=='label':
                menu[name].setdefault('label', html.a())(value)
                continue
            elif prop_name=='path_info':
                menu[name]['if_path_info'] = re.match(value, req.path_info) and True or False
            menu[name][prop_name]=value
        return menu, options
