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
    'models',
    'views/common',
    'views/dialogs',
    'text!templates/cluster/network_tab.html',
    'text!templates/cluster/network.html',
    'text!templates/cluster/range_field.html',
    'text!templates/cluster/nova_nameservers.html',
    'text!templates/cluster/neutron_parameters.html',
    'text!templates/cluster/verify_network_control.html'
],
function(utils, models, commonViews, dialogViews, networkTabTemplate, networkTemplate, rangeTemplate, novaNetworkConfigurationTemplate, neutronParametersTemplate, networkTabVerificationControlTemplate) {
    'use strict';
    var NetworkTab, Network, NeutronConfiguration, NovaNetworkConfiguration, NetworkTabVerificationControl;

    NetworkTab = commonViews.Tab.extend({
        template: _.template(networkTabTemplate),
        updateInterval: 3000,
        hasChanges: false,
        events: {
            'click .verify-networks-btn:not([disabled])': 'verifyNetworks',
            'click .btn-revert-changes:not([disabled])': 'revertChanges',
            'click .apply-btn:not([disabled])': 'applyChanges'
        },
        bindings: {'input[name=net-manager]': 'net_manager'},
        defaultButtonsState: function(errors) {
            this.$('.btn.verify-networks-btn').attr('disabled', errors);
            this.$('.btn.btn-revert-changes').attr('disabled', !this.hasChanges && !errors);
            this.$('.btn.apply-btn').attr('disabled', !this.hasChanges || errors);
        },
        disableControls: function() {
            this.$('.btn, input, select').attr('disabled', true);
        },
        isLocked: function() {
            var task = !!this.model.task('deploy', 'running') || !!this.model.task('verify_networks', 'running');
            return this.model.get('status') != 'new' || task;
        },
        isVerificationLocked: function() {
            return !!this.model.task('deploy', 'running') || !!this.model.task('verify_networks', 'running');
        },
        checkForChanges: function() {
            this.hasChanges = !_.isEqual(this.model.get('networkConfiguration').toJSON(), this.networkConfiguration.toJSON());
            this.defaultButtonsState(!!this.networkConfiguration.validationError);
        },
        changeManager: function(networkConfiguration, net_manager) {
            networkConfiguration.get('networks').findWhere({name: 'fixed'}).set({amount: net_manager == 'VlanManager' ? this.fixedAmount : 1});
            this.renderNetworks();
            this.updateNetworkConfiguration();
        },
        startVerification: function() {
            var task = new models.Task();
            var options = {
                method: 'PUT',
                url: _.result(this.model, 'url') + '/network_configuration/' + this.model.get('net_provider') + '/verify',
                data: JSON.stringify(this.networkConfiguration)
            };
            task.save({}, options)
                .fail(_.bind(function() {
                    utils.showErrorDialog({title: 'Network verification'});
                    this.$('.verify-networks-btn').prop('disabled', false);
                }, this))
                .always(_.bind(function() {
                    this.model.get('tasks').fetch({data: {cluster_id: this.model.id}}).done(_.bind(this.scheduleUpdate, this));
                }, this));
        },
        verifyNetworks: function() {
            if (!this.networkConfiguration.validationError) {
                this.$('.verify-networks-btn').prop('disabled', true);
                this.filterEmptyIpRanges();
                this.page.removeFinishedTasks().always(_.bind(this.startVerification, this));
            }
        },
        revertChanges: function() {
            this.setInitialData();
            this.page.removeFinishedTasks().always(_.bind(this.render, this));
        },
        filterEmptyIpRanges: function() {
            this.networkConfiguration.get('networks').each(function(network) {
                network.set({ip_ranges: _.filter(network.get('ip_ranges'), function(range) {return _.compact(range).length;})});
            }, this);
        },
        applyChanges: function() {
            var deferred;
            if (!this.networkConfiguration.validationError) {
                this.disableControls();
                this.filterEmptyIpRanges();
                deferred = Backbone.sync('update', this.networkConfiguration, {url: _.result(this.model, 'url') + '/network_configuration/' + this.model.get('net_provider')})
                    .done(_.bind(function(task) {
                        if (task && task.status == 'error') {
                            this.page.removeFinishedTasks().always(_.bind(function() {
                                this.defaultButtonsState(false);
                                this.model.fetch();
                                this.model.fetchRelated('tasks');
                            }, this));
                        } else {
                            this.hasChanges = false;
                            this.model.set({networkConfiguration: new models.NetworkConfiguration(this.networkConfiguration.toJSON(), {parse: true})});
                            this.model.fetch();
                            this.model.fetchRelated('tasks');
                        }
                    }, this))
                    .fail(_.bind(function() {
                        utils.showErrorDialog({title: 'Networks'});
                        this.defaultButtonsState(false);
                        this.model.fetch();
                        this.model.fetchRelated('tasks');
                    }, this));
            } else {
                deferred = new $.Deferred();
                deferred.reject();
            }
            return deferred;
        },
        scheduleUpdate: function() {
            if (this.model.task('verify_networks', 'running')) {
                this.registerDeferred($.timeout(this.updateInterval).done(_.bind(this.update, this)));
            }
        },
        update: function() {
            var task = this.model.task('verify_networks', 'running');
            if (task) {
                this.registerDeferred(task.fetch().always(_.bind(this.scheduleUpdate, this)));
            }
        },
        bindTaskEvents: function(task) {
            if (task.get('name') == 'verify_networks' || task.get('name') == 'deploy' || task.get('name') == 'check_networks') {
                return task.on('change:status', this.render, this);
            }
            return null;
        },
        onNewTask: function(task) {
            return this.bindTaskEvents(task) && this.render();
        },
        setInitialData: function() {
            this.hasChanges = false;
            this.networkConfiguration = new models.NetworkConfiguration(this.model.get('networkConfiguration').toJSON(), {parse: true});
            this.networkConfiguration.get('networks').each(function(network) {
                if (!_.contains(['fixed', 'private'], network.get('name'))) {
                    network.set({network_size: utils.calculateNetworkSize(network.get('cidr'))});
                }
            });
            this.fixedAmount = this.model.get('net_provider') == 'nova_network' ? this.networkConfiguration.get('networks').findWhere({name: 'fixed'}).get('amount') : 1;
            this.networkConfiguration.on('invalid', function(model, errors) {
                _.each(errors.dns_nameservers, _.bind(function(error, field) {
                    this.$('.nova-nameservers input[name=' + field + ']').addClass('error').parents('.network-attribute').find('.error .help-inline').text(error);
                }, this));
                _.each(errors.neutron_parameters, _.bind(function(error, field) {
                    this.$('.neutron-parameters input[name=' + field + ']').addClass('error').parents('.network-attribute').find('.error .help-inline').text(error);
                }, this));
                _.each(errors.networks, _.bind(function(networkErrors, network) {
                    _.each(networkErrors, _.bind(function(error, field) {
                        if (field != 'ip_ranges') {
                            this.$('input[name=' + network + '-' + field + ']').addClass('error').parents('.network-attribute').find('.error .help-inline').text(error);
                        } else {
                            _.each(networkErrors.ip_ranges, _.bind(function(range) {
                                var row = this.$('.' + network + ' .ip-range-rows .range-row:eq(' + range.index + ')');
                                row.find('input:first').toggleClass('error', !!range.start);
                                row.find('input:last').toggleClass('error', !!range.end);
                                row.find('.help-inline').text(range.start || range.end);
                            }, this));
                        }
                    }, this));
                }, this));
            }, this);
            this.networkConfiguration.on('change:net_manager', this.changeManager, this);
        },
        updateNetworkConfiguration: function() {
            this.$('input[type=text]').removeClass('error').parents('.network-attribute').find('.help-inline').text('');
            this.networkConfiguration.isValid();
            this.checkForChanges();
            this.page.removeFinishedTasks();
        },
        initialize: function(options) {
            _.defaults(this, options);
            this.networkConfiguration = new models.NetworkConfiguration();
            this.model.on('change:status', this.render, this);
            this.model.get('tasks').each(this.bindTaskEvents, this);
            this.model.get('tasks').on('add', this.onNewTask, this);
            this.model.get('tasks').on('remove', this.renderVerificationControl, this);
            if (!this.model.get('networkConfiguration')) {
                this.model.set({networkConfiguration: new models.NetworkConfiguration()});
                this.loading = this.model.get('networkConfiguration').fetch({url: _.result(this.model, 'url') + '/network_configuration/' + this.model.get('net_provider')})
                    .done(_.bind(function() {
                        this.setInitialData();
                        this.render();
                    }, this));
            } else {
                this.setInitialData();
            }
        },
        showVerificationErrors: function() {
            var task = this.model.task('verify_networks', 'error') || this.model.task('check_networks', 'error');
            if (task && task.get('result').length) {
                _.each(task.get('result'), function(failedNetwork) {
                    _.each(failedNetwork.errors, function(field) {
                        this.$('div[data-network-id=' + failedNetwork.id + ']').find('.' + field).children().addClass('error');
                    }, this);
                   _.each(failedNetwork.range_errors, function (idx) {
                        this.$('div[data-network-id=' + failedNetwork.id + ']').find('.range-row:eq('+idx+') input').addClass('error');
                    }, this);
                }, this);
            }
        },
        renderVerificationControl: function() {
            var verificationView = new NetworkTabVerificationControl({
                cluster: this.model,
                networks: this.networkConfiguration.get('networks')
            });
            this.registerSubView(verificationView);
            this.$('.verification-control').html(verificationView.render().el);
            this.showVerificationErrors();
        },
        renderNetworks: function() {
            if (this.networkConfiguration.get('networks')) {
                this.tearDownRegisteredSubViews();
                this.$('.networks-table').html('');
                this.networkConfiguration.get('networks').each(function(network) {
                    var networkView = new Network({network: network, tab: this});
                    this.registerSubView(networkView);
                    this.$('.networks-table').append(networkView.render().el);
                }, this);
            }
        },
        renderNovaNetworkConfiguration: function() {
            if (this.model.get('net_provider') == 'nova_network' && this.networkConfiguration.get('dns_nameservers')) {
                var novaNetworkConfigurationView = new NovaNetworkConfiguration({
                    configuration: this.networkConfiguration.get('dns_nameservers'),
                    tab: this
                });
                this.registerSubView(novaNetworkConfigurationView);
                this.$('.nova-nameservers').html(novaNetworkConfigurationView.render().el);
            }
        },
        renderNeutronConfiguration: function() {
            if (this.model.get('net_provider') == 'neutron' && this.networkConfiguration.get('neutron_parameters')) {
                var neutronConfigurationView = new NeutronConfiguration({
                    configuration: this.networkConfiguration.get('neutron_parameters'),
                    tab: this
                });
                this.registerSubView(neutronConfigurationView);
                this.$('.neutron-parameters').html(neutronConfigurationView.render().el);
            }
        },
        render: function() {
            this.$el.html(this.template({
                loading: this.loading,
                net_provider: this.model.get('net_provider'),
                hasChanges: this.hasChanges,
                locked: this.isLocked(),
                verificationLocked: this.isVerificationLocked(),
                segment_type: this.model.get("net_segment_type")
            })).i18n();
            this.stickit(this.networkConfiguration);
            this.renderNetworks();
            this.renderNovaNetworkConfiguration();
            this.renderNeutronConfiguration();
            this.renderVerificationControl();
            return this;
        }
    });

    Network = Backbone.View.extend({
        template: _.template(networkTemplate),
        rangeTemplate: _.template(rangeTemplate),
        events: {
            'click .ip-ranges-add:not([disabled])': 'addIPRange',
            'click .ip-ranges-delete:not([disabled])': 'deleteIPRange'
        },
        stickitNetwork: function() {
            var bindings = {
                '.cidr input': 'cidr',
                '.netmask input': 'netmask',
                '.gateway input': 'gateway',
                '.amount input': {
                    observe: 'amount',
                    onSet: function(value) {
                        return Number(value);
                    }
                },
                '.fixed select[name=network_size]': {
                    observe: 'network_size',
                    selectOptions: {
                        collection: function() {
                            return _.map([8, 16, 32, 64, 128, 256, 512, 1024, 2048], function(size) {
                                return {value: size, label: size};
                            });
                        }
                    }
                },
                '.use-vlan-tagging': {
                    observe: 'vlan_start',
                    onGet: function(value) {
                        return !_.isNull(value);
                    },
                    onSet: function(value) {
                        return value ? '' : null;
                    },
                    attributes: [{
                        name: 'disabled',
                        observe: 'name',
                        onGet: function(value) {
                            return value == 'floating';
                        }
                    }]
                },
                'input.vlan': {
                    observe: 'vlan_start',
                    onGet: function(value) {
                        this.$('input.vlan').toggle(!_.isNull(value));
                        return value;
                    },
                    onSet: function(value) {
                        return Number(value);
                    },
                    attributes: [{
                        name: 'disabled',
                        observe: 'name',
                        onGet: function(value) {
                            return value == 'floating';
                        }
                    }]
                },
                '.fixed input[name=vlan_end]': {
                    observe: ['vlan_start', 'amount'],
                    onGet: function(value) {
                        var vlanEnd = value[0] + value[1] - 1;
                        return vlanEnd > 4094 ? 4094 : vlanEnd;
                    }
                }
            };
            this.stickit(this.network, bindings);
        },
        updateFloatingVlan: function(network, vlan) {
            if (network.get('name') == 'public' && this.tab.model.get('net_provider') == 'nova_network') {
                this.tab.networkConfiguration.get('networks').findWhere({name: 'floating'}).set({vlan_start: vlan});
            }
        },
        changeIpRanges: function(e, addRange) {
            var index = this.$('.range-row').index($(e.currentTarget).parents('.range-row'));
            var ipRanges = _.clone(this.network.get('ip_ranges'));
            if (addRange) {
                ipRanges.splice(index + 1, 0, ['','']);
            } else {
                ipRanges.splice(index, 1);
            }
            this.network.set({ip_ranges: ipRanges});
            this.renderIpRanges();
        },
        addIPRange: function(e) {
            this.changeIpRanges(e, true);
        },
        deleteIPRange: function(e) {
            this.changeIpRanges(e, false);
        },
        initialize: function(options) {
            _.defaults(this, options);
            this.network.on('change:vlan_start', this.updateFloatingVlan, this);
            this.network.on('change:amount', function(network, amount) {this.tab.fixedAmount = amount;}, this);
            this.network.on('change', this.tab.updateNetworkConfiguration, this.tab);
        },
        renderIpRanges: function() {
            this.$('.ip-ranges-rows').empty();
            _.each(this.network.get('ip_ranges'), function(range, i) {
                this.$('.ip-ranges-rows').append(this.rangeTemplate({
                    index: i,
                    rangeControls: true,
                    removalPossible: i < this.network.get('ip_ranges').length - 1,
                    locked: this.tab.isLocked()
                }));
                var ipRangeBindings = {};
                _.each(range, function(ip, index) {
                    ipRangeBindings['.ip-ranges-rows .range' + index + '[data-range=' + i + ']'] = {
                        observe: 'ip_ranges',
                        stickitChange: i,
                        onGet: function(value) {
                            return value[i][index];
                        },
                        onSet: _.bind(function(value, options) {
                            var ipRanges = this.network.get('ip_ranges');
                            ipRanges[options.stickitChange][index] = value;
                            return ipRanges;
                        }, this)
                    };
                }, this);
                this.stickit(this.network, ipRangeBindings);
            }, this);
        },
        render: function() {
            this.$el.html(this.template({
                network: this.network,
                net_manager: this.tab.networkConfiguration.get('net_manager'),
                shownAttributes: this.network.getAttributes(this.tab.model.get('net_provider')),
                locked: this.tab.isLocked()
            })).i18n();
            this.renderIpRanges();
            this.stickitNetwork();
            return this;
        }
    });

    NovaNetworkConfiguration = Backbone.View.extend({
        template: _.template(novaNetworkConfigurationTemplate),
        rangeTemplate: _.template(rangeTemplate),
        initialize: function(options) {
            _.defaults(this, options);
            this.configuration.on('change', this.tab.updateNetworkConfiguration, this.tab);
        },
        stickitNameservers: function() {
            var bindings = {};
            _.each(this.configuration.get('nameservers'), function(nameserver, i) {
                bindings['.nameservers-row input.range' + i] = {
                    observe: 'nameservers',
                    stickitChange: i,
                    onGet: function(value) {return value[i];},
                    onSet: _.bind(function(value, options) {
                        var nameservers = this.configuration.get('nameservers');
                        nameservers[options.stickitChange] = value;
                        return nameservers;
                    }, this)
                };
            }, this);
            this.stickit(this.configuration, bindings);
        },
        render: function() {
            this.$el.html(this.template()).i18n();
            this.$('.nameservers-row').html(this.rangeTemplate({
                index: 0,
                rangeControls: false,
                locked: this.tab.isLocked()
            }));
            this.stickitNameservers();
            return this;
        }
    });

    NeutronConfiguration = Backbone.View.extend({
        template: _.template(neutronParametersTemplate),
        rangeTemplate: _.template(rangeTemplate),
        initialize: function(options) {
            _.defaults(this, options);
            this.configuration.on('change', this.tab.updateNetworkConfiguration, this.tab);
        },
        stickitConfiguration: function() {
            var bindings = {
                'input[name=base_mac]': 'L2.base_mac',
                'input[name=cidr-int]': 'predefined_networks.net04.L3.cidr',
                'input[name=gateway]': 'predefined_networks.net04.L3.gateway'
            };
            var idRange = this.configuration.get('segmentation_type') == 'gre' ? this.configuration.get('L2').tunnel_id_ranges : this.configuration.get('L2').phys_nets.physnet2.vlan_range;
            _.each(idRange, function(id, i) {
                bindings['.id-row input.range' + i] = {
                    observe: ['L2.tunnel_id_ranges', 'L2.phys_nets.physnet2.vlan_range'],
                    stickitChange: i,
                    onGet: function(value) {return value[0] ? value[0][i] : value[1][i];},
                    onSet: _.bind(function(value, options) {
                        var range = this.configuration.get('segmentation_type') == 'gre' ? this.configuration.get('L2').tunnel_id_ranges : this.configuration.get('L2').phys_nets.physnet2.vlan_range;
                        range[options.stickitChange] = Number(value);
                        return range;
                    }, this)
                };
            }, this);
            this.composeRangeBindings(this.configuration.get('predefined_networks').net04_ext.L3.floating, '.floating-row', 'predefined_networks.net04_ext.L3.floating', bindings);
            this.composeRangeBindings(this.configuration.get('predefined_networks').net04.L3.nameservers, '.nameservers-row', 'predefined_networks.net04.L3.nameservers', bindings);
            this.stickit(this.configuration, bindings);
        },
        composeRangeBindings: function(range, domSelector, attribute, bindings) {
            _.each(range, function(el, i) {
                bindings[domSelector + ' input.range' + i] = {
                    observe: attribute,
                    stickitChange: i,
                    onGet: function(value) {return value[i];},
                    onSet: function(value, options) {
                        range[options.stickitChange] = value;
                        return range;
                    }
                };
            });
        },
        render: function() {
            this.$el.html(this.template({
                segmentation: this.configuration.get('segmentation_type'),
                locked: this.tab.isLocked()
            })).i18n();
            var defaultTemplateData = {
                index: 0,
                rangeControls: false,
                locked: this.tab.isLocked()
            };
            this.$('.id-row').html(this.rangeTemplate(defaultTemplateData));
            this.$('.floating-row').html(this.rangeTemplate(defaultTemplateData));
            this.$('.nameservers-row').html(this.rangeTemplate(defaultTemplateData));
            this.stickitConfiguration();
            return this;
        }
    });

    NetworkTabVerificationControl = Backbone.View.extend({
        template: _.template(networkTabVerificationControlTemplate),
        initialize: function(options) {
            _.defaults(this, options);
        },
        render: function() {
            this.$el.html(this.template({
                cluster: this.cluster,
                networks: this.networks
            })).i18n();
            return this;
        }
    });

    return NetworkTab;
});
