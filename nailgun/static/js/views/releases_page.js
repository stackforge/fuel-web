/*
 * Copyright 2013 Mirantis, Inc.
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
    'utils',
    'views/common',
    'views/dialogs',
    'text!templates/release/list.html',
    'text!templates/release/release.html'
],
function(utils, commonViews, dialogViews, releasesListTemplate, releaseTemplate) {
    'use strict';

    var ReleasesPage, Release;

    ReleasesPage = commonViews.Page.extend({
        navbarActiveElement: 'releases',
        breadcrumbsPath: [['Home', '#'], 'Releases'],
        title: 'Releases',
        updateInterval: 5000,
        template: _.template(releasesListTemplate),
        scheduleUpdate: function() {
            if (this.tasks.filterTasks({name: 'redhat_setup', status: 'running'}).length) {
                if (this.timeout) {
                    this.timeout.clear();
                }
                this.registerDeferred(this.timeout = $.timeout(this.updateInterval).done(_.bind(this.update, this)));
            }
        },
        update: function() {
            this.registerDeferred(this.tasks.fetch().always(_.bind(this.scheduleUpdate, this)));
        },
        initialize: function(options) {
            _.defaults(this, options);
            this.scheduleUpdate();
        },
        render: function() {
            this.tearDownRegisteredSubViews();
            this.$el.html(this.template({releases: this.collection}));
            this.collection.each(function(release) {
                var releaseView = new Release({release: release, page: this});
                this.registerSubView(releaseView);
                this.$('.releases-table tbody').append(releaseView.render().el);
            }, this);
            return this;
        }
    });

    Release = Backbone.View.extend({
        tagName: 'tr',
        template: _.template(releaseTemplate),
        'events': {
            'click .btn-rhel-setup': 'showRhelLicenseCredentials'
        },
        releaseBindings: {
           '.release-download-progress': {
                observe: 'state',
                visible: function(value) {
                    return value == 'downloading';
                }
            },
            '.release-state': {
                observe: 'state',
                visible: function(value) {
                    return value != '';
                },
                updateView: true,
                onGet: function(value) {
                    return {available: 'Active', error: 'Error', not_available: 'Not available'}[value] || '';
                },
                attributes: [{name: 'class'}]
            }
        },
        taskBindings: {
           '.release-download-progress .bar-title span': {
                observe: 'progress',
                onGet: function(value) {
                    return value + '%';
                }
            },
           '.release-download-progress .bar': {
                observe: 'progress',
                update: function($el, value) {
                    $el.css('width', value + '%');
                }
            },
           '.release-error': 'message'
        },
        showRhelLicenseCredentials: function() {
            var dialog = new dialogViews.RhelCredentialsDialog({release: this.release});
            this.registerSubView(dialog);
            dialog.render();
        },
        checkForSetupCompletion: function() {
            var setupTask = this.page.tasks.findTask({name: 'redhat_setup', status: ['ready', 'error'], release: this.release.id});
            if (setupTask) {
                if (setupTask.get('status') == 'ready') {
                    setupTask.destroy();
                }
                this.release.fetch();
                app.navbar.refresh();
            }
        },
        initialize: function(options) {
            _.defaults(this, options);
            this.page.tasks.each(this.bindTaskEvents, this);
            this.page.tasks.on('add', this.onNewTask, this);
        },
        bindTaskEvents: function(task) {
            if (task.get('name') == 'redhat_setup' && task.releaseId() == this.release.id) {
                if (task.get('status') == 'running') {
                    task.on('change:status', this.checkForSetupCompletion, this);
                }
                return task;
            }
            return null;
        },
        setupTaskBindings: function(task) {
            if (task.get('name') == 'redhat_setup' && task.releaseId() == this.release.id) {
                this.stickit(task, this.taskBindings);
            }
        },
        onNewTask: function(task) {
            if (this.bindTaskEvents(task)) {
                this.setupTaskBindings(task);
                this.checkForSetupCompletion();
            }
        },
        render: function() {
            this.tearDownRegisteredSubViews();
            this.$el.html(this.template({release: this.release}));
            this.stickit(this.release, this.releaseBindings);
            this.page.tasks.each(this.setupTaskBindings, this);
            return this;
        }
    });

    return ReleasesPage;
});
