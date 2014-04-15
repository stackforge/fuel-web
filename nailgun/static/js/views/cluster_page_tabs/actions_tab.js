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
    'models',
    'views/common',
    'views/dialogs',
    'text!templates/cluster/actions_tab.html'
],
function(models, commonViews, dialogViews, actionsTabTemplate) {
    'use strict';

    var ActionsTab = commonViews.Tab.extend({
        template: _.template(actionsTabTemplate),
        events: {
            'click .apply-name-btn': 'applyNewClusterName',
            'keydown .rename-cluster-form input': 'onClusterNameInputKeydown',
            'click .delete-cluster-btn': 'deleteCluster',
            'click .reset-environment-btn': 'resetEnvironment',
            'click .update-btn': 'updateEnvironment',
            'click .rollback-btn': 'rollbackEnvironment'
        },
        bindings: {
            'select[name=update_release]': {
                observe: 'pending_release_id',
                selectOptions: {
                    collection:function() {
                        return this.releases.map(function(release) {
                            return {value: release.id, label: release.get('name') + ' (' + release.get('openstack_version') + ')'};
                        });
                    },
                    defaultOption: {
                        label: $.t('cluster_page.actions_tab.choose_release'),
                        value: null
                    }
                },
                attributes: [{
                    name: 'disabled',
                    onGet: function() {return this.model.task({group: 'deployment', status: 'running'});}
                }]
            },
            '.update-btn': {
                attributes: [{
                    name: 'disabled',
                    observe: 'pending_release_id',
                    onGet: function(value) {return _.isNull(value) || this.model.task({group: 'deployment', status: 'running'});}
                }]
            }
        },
        applyNewClusterName: function() {
            var name = $.trim(this.$('.rename-cluster-form input').val());
            if (name != this.model.get('name')) {
                var deferred = this.model.save({name: name}, {patch: true, wait: true});
                if (deferred) {
                    var controls = this.$('.rename-cluster-form input, .rename-cluster-form button');
                    controls.attr('disabled', true);
                    deferred
                        .fail(_.bind(function(response) {
                            if (response.status == 409) {
                                this.model.trigger('invalid', this.model, {name: response.responseText});
                            }
                        }, this))
                        .always(_.bind(function() {
                            controls.attr('disabled', false);
                        }, this));
                }
            }
        },
        showValidationError: function(model, error) {
            this.$('.rename-cluster-form input[type=text]').addClass('error');
            this.$('.text-error').text(_.values(error).join('; ')).show();
        },
        onClusterNameInputKeydown: function(e) {
            this.$('.rename-cluster-form input[type=text]').removeClass('error');
            this.$('.text-error').hide();
        },
        deleteCluster: function() {
            this.registerSubView(new dialogViews.RemoveClusterDialog({model: this.model})).render();
        },
        resetEnvironment: function() {
            this.registerSubView(new dialogViews.ResetEnvironmentDialog({model: this.model})).render();
        },
        bindTaskEvents: function(task) {
            return task.match({group: 'deployment'}) ? task.on('change:status', this.render, this) : null;
        },
        onNewTask: function(task) {
            return this.bindTaskEvents(task) && this.render();
        },
        rollbackEnvironment: function(task) {
            this.model.set({pending_release_id: this.model.get('release_id')});
            this.registerSubView(new dialogViews.RollbackEnvironmentDialog({model: this.model})).render();
        },
        updateEnvironment: function(task) {
            this.registerSubView(new dialogViews.UpdateEnvironmentDialog({model: this.model})).render();
        },
        initialize: function(options) {
            _.defaults(this, options);
            this.releases = new models.Releases();
            var cluster = this.model;
            var operatingSystem = cluster.get('release').get('operating_system');
            var openstackVersion = cluster.get('release').get('openstack_version');
            this.releases.parse = function(response) {
                return _.filter(response, function(release) {
                    return _.contains(release.can_update_openstack_versions, openstackVersion) && release.operating_system == operatingSystem;
                });
            };
            this.releases.fetch().done(_.bind(this.render, this));
            cluster.on('change:name change:status', this.render, this);
            cluster.get('tasks').each(this.bindTaskEvents, this);
            cluster.get('tasks').on('add', this.onNewTask, this);
            cluster.on('invalid', this.showValidationError, this);
        },
        render: function() {
            this.$el.html(this.template({
                cluster: this.model,
                releases: this.releases,
                isResetDisabled: this.model.get('status') == 'new' || this.model.task({group: 'deployment', status: 'running'})
            })).i18n();
            this.stickit();
            return this;
        }
    });

    return ActionsTab;
});
