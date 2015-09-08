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

define(['underscore', 'intern/dojo/node!fs', 'intern/dojo/node!leadfoot/Command'], function(_, fs, Command) {
    'use strict';

    _.defaults(Command.prototype, {
        clickByLinkText: function(cssSelector, linkText) {
            return new this.constructor(this, function() {
                return this.parent
                    .setFindTimeout(1000)
                    .findAllByCssSelector(cssSelector)
                    .then(function(links) {
                        return links.reduce(function(matchFound, link) {
                            return link.getVisibleText().then(function(text) {
                                if (_.trim(text) == linkText) {
                                    link.click();
                                    return true;
                                }
                                return matchFound;
                            });
                        }, false);
                    });
            });
        },
        clickByCssSelector: function(cssSelector) {
            return new this.constructor(this, function() {
                var currentTimeout = 0;
                return this.parent
                    .getFindTimeout()
                    .then(function(value) {
                        currentTimeout = value;
                    })
                    .setFindTimeout(1000)
                    .findByCssSelector(cssSelector)
                        .click()
                        .end()
                    .setFindTimeout(currentTimeout);
            });
        },
        takeScreenshotAndSave: function(filename) {
            return new this.constructor(this, function() {
                return this.parent
                    .takeScreenshot()
                    .then(function(buffer) {
                        var targetDir = process.env.ARTIFACTS || process.cwd();
                        if (!filename) filename = new Date().toTimeString();
                        filename = filename.replace(/\s/g, '_');
                        filename = targetDir + '/' + filename + '.png';
                        console.log('Saving screenshot to', filename); // eslint-disable-line no-console
                        fs.writeFileSync(filename, buffer);
                });
            });
        },
        waitForCssSelector: function(cssSelector, timeout) {
            // used to wait until the element will appear with custom timeout
            return new this.constructor(this, function() {
                var self = this,
                    currentTimeout = 0;
                return this.parent
                    .getFindTimeout()
                    .then(function(value) {
                        currentTimeout = value;
                    })
                    .setFindTimeout(timeout)
                    .findByCssSelector(cssSelector)
                        .end()
                    .catch(function(error) {
                        self.setFindTimeout(currentTimeout);
                        throw error;
                    })
                    .setFindTimeout(currentTimeout);
            });
        },
        waitForElementDeletion: function(cssSelector, timeout) {
            // used to wait until the element will disappear with custom timeout
            return new this.constructor(this, function() {
                var self = this,
                    currentTimeout = 0;
                return this.parent
                    .getFindTimeout()
                    .then(function(value) {
                        currentTimeout = value;
                    })
                    .setFindTimeout(timeout)
                    .waitForDeletedByCssSelector(cssSelector)
                    .catch(function(error) {
                        self.setFindTimeout(currentTimeout);
                        // For cases when element is destroyed already
                        if (error.name != 'Timeout')
                            throw error;
                    })
                    .setFindTimeout(currentTimeout);
            });
        }
    });

    var serverHost = '127.0.0.1',
        serverPort = process.env.SERVER_PORT || 5544,
        serverUrl = 'http://' + serverHost + ':' + serverPort,
        username = 'admin',
        password = 'admin';

    return {
        username: username,
        password: password,
        serverUrl: serverUrl
    };
});
