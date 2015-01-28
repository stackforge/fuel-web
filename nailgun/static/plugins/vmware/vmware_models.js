/*
 * Copyright 2014 Mirantis, Inc.
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
    'jquery',
    'underscore',
    'i18n',
    'backbone',
    'utils',
    'deepModel',
    'backbone-lodash-monkeypatch'
],
function() {
    'use strict';

    console.log('VmWare models loaded'); //TODO

    var VCenter = Backbone.Model.extend({
        constructorName: 'VCenter',
        urlRoot: function() {
            return '/api/vmware/' + this.id + '/settings';
        },
        //constructor: function() {
        //    //this.id = clusterId;
        //},
        parse: function(response) {
            console.log(response);
        }
    });
    console.log(VCenter);

    return {
        VCenter: VCenter
    };
});
