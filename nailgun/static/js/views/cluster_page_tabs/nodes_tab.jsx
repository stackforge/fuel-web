/*
 * Copyright 2015 Mirantis, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
**/
define(
[
    'underscore',
    'react',
    'jsx!backbone_view_wrapper',
    'jsx!views/cluster_page_tabs/nodes_tab_screens/cluster_nodes_screen',
    'jsx!views/cluster_page_tabs/nodes_tab_screens/add_nodes_screen',
    'jsx!views/cluster_page_tabs/nodes_tab_screens/edit_nodes_screen',
    'views/cluster_page_tabs/nodes_tab_screens/edit_node_disks_screen',
    'views/cluster_page_tabs/nodes_tab_screens/edit_node_interfaces_screen'
],
function(_, React, BackboneViewWrapper, ClusterNodesScreen, AddNodesScreen, EditNodesScreen, EditNodeDisksScreen, EditNodeInterfacesScreen) {
    'use strict';

    var ReactCSSTransitionGroup = React.addons.CSSTransitionGroup;

    var NodesTab = React.createClass({
        getInitialState: function() {
            return {screen: this.props.tabOptions[0] || 'list'};
        },
        hasChanges: function() {
            return _.result(this.refs.screen.refs.screen, 'hasChanges');
        },
        revertChanges: function() {
            return this.refs.screen.refs.screen.revertChanges();
        },
        getAvailableScreens: function() {
            return {
                list: ClusterNodesScreen,
                add: AddNodesScreen,
                edit: EditNodesScreen,
                disks: BackboneViewWrapper(EditNodeDisksScreen),
                interfaces: BackboneViewWrapper(EditNodeInterfacesScreen)
            };
        },
        checkScreen: function(props) {
            props = props || this.props;
            var newScreen = props.tabOptions[0];
            if (newScreen && !this.getAvailableScreens()[newScreen]) {
                app.navigate('cluster/' + props.cluster.id + '/nodes', {trigger: true, replace: true});
                return;
            }
        },
        componentWillMount: function() {
            this.checkScreen();
        },
        componentWillReceiveProps: function(nextProps) {
            this.checkScreen(nextProps);
            this.setState({screen: nextProps.tabOptions[0] || 'list'});
        },
        render: function() {
            var Screen = this.getAvailableScreens()[this.state.screen];
            if (!Screen) return null;
            var screenView = <Screen
                ref='screen'
                key={'screen' + this.state.screen}
                cluster={this.props.cluster}
                screenOptions={this.props.tabOptions.slice(1)}
            />;
            return (
                <ReactCSSTransitionGroup component='div' className='wrapper' transitionName='screen'>
                    {screenView}
                </ReactCSSTransitionGroup>
            );
        }
    });

    return NodesTab;
});
