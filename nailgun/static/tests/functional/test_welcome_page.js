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

define([
    'intern!object',
    'intern/chai!assert',
    'tests/functional/pages/login',
    'tests/functional/pages/welcome'
], function(registerSuite, assert, LoginPage, WelcomePage) {
    'use strict';

    registerSuite(function() {
        var loginPage,
            welcomePage;

        return {
            name: 'Welcome page',
            setup: function() {
                loginPage = new LoginPage(this.remote);
                welcomePage = new WelcomePage(this.remote);
            },
            'Skip welcome page': function() {
                return loginPage.login()
                    .then(function() {
                        return welcomePage.skip()
                            .then(function(result) {
                                assert.isTrue(result, 'Start using fuel button is present');
                            });
                    });

            }
        };
    });
});
