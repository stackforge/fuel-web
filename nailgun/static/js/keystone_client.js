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
define(['jquery'], function($) {
    'use strict';

    function KeystoneClient(url, options) {
        _.extend(this, {
            url: url,
            cacheTokenFor: 10 * 1000
        }, options);
        if (!(this.username && this.password) && !this.token) {
            throw new Error('You must specify username/password or token');
        }
    }

    _.extend(KeystoneClient.prototype, {
        updateToken: function() {
            if (this.tokenUpdateRequest) {
                return this.tokenUpdateRequest;
            }
            if (this.tokenUpdateTime && (this.cacheTokenFor > (new Date() - this.tokenUpdateTime))) {
                return $.Deferred().resolve();
            }
            var data = {auth: {}};
            if (this.tenantName) {
                data.auth.tenantName = this.tenantName;
            }
            if (this.username && this.password) {
                data.auth.passwordCredentials = _.pick(this, ['username', 'password']);
                delete this.username;
                delete this.password;
            } else {
                data.auth.token = {id: this.token};
            }
            this.tokenUpdateRequest = $.ajax(this.url + '/tokens', {
                type: 'POST',
                dataType: 'json',
                contentType: 'application/json',
                headers: {Accept: 'application/json'},
                data: JSON.stringify(data)
            }).then(_.bind(function(result, state, deferred) {
                if (result.access) {
                    this.token = result.access.token.id;
                    this.tokenUpdateTime = new Date();
                    return deferred;
                } else {
                    return $.Deferred().reject();
                }
            }, this)).always(_.bind(function() {
                delete this.tokenUpdateRequest;
            }, this));
            return this.tokenUpdateRequest;
        }
    });

    return KeystoneClient;
});
