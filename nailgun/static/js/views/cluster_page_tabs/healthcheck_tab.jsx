/*
 * Copyright 2014 Mirantis, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the 'License'); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 **/
define(
    [
        'react',
        'models',
        'utils',
        'jsx!component_mixins'
    ],
    function (React, models, utils, componentMixins) {
        'use strict';

        var ReactCSSTransitionGroup = React.addons.CSSTransitionGroup;
        var HealthCheckTab = React.createClass({
            mixins: [
                React.BackboneMixin({modelOrCollection: function(props) {
                    return props.model.get('tasks');
                }}),
                React.BackboneMixin({modelOrCollection: function(props) {
                    return props.model;
                }})
            ],
            getInitialState: function () {
                var ostf = {},
                    model = this.props.model;
                ostf.testsets = new models.TestSets();
                ostf.testsets.url = _.result(ostf.testsets, 'url') + '/' + model.id;
                ostf.tests = new models.Tests();
                ostf.tests.url = _.result(ostf.tests, 'url') + '/' + model.id;
                ostf.testruns = new models.TestRuns();
                ostf.testruns.url = _.result(ostf.testruns, 'url') + '/last/' + model.id;
                return {ostf: ostf};
            },
            componentDidMount: function() {
                $.when(
                    this.state.ostf.testsets.deferred =  this.state.ostf.testsets.fetch(),
                    this.state.ostf.tests.fetch(),
                    this.state.ostf.testruns.fetch()
                )
                .always(_.bind(function() {
                        this.forceUpdate();
                }, this));
            },
            render: function () {
                return (
                    <HealthcheckTabContent
                        testsets={this.state.ostf.testsets}
                        tests={this.state.ostf.tests}
                        testruns={this.state.ostf.testruns}
                        cluster={this.props.model}
                    />
                );
            }
        });

        var HealthcheckTabContent = React.createClass({
            mixins: [
                React.BackboneMixin('tests'),
                React.BackboneMixin('testsets'),
                React.BackboneMixin('testruns', 'sync'),
                componentMixins.pollingMixin(1)
            ],
            shouldDataBeFetched: function() {
                return !!this.props.testruns.where({status: 'running'}).length;
            },
            fetchData: function() {
                return this.props.testruns.fetch();
            },
            getInitialState: function () {
                return {credentialsVisible: false};
            },
            isLocked: function () {
                var model = this.props.cluster;
                return model.get('status') == 'new' || !!model.task({group: 'deployment', status: 'running'});
            },
            getNumberOfCheckedTests: function () {
                return this.props.tests.where({checked: true}).length;
            },
            toggleCredentials: function () {

             $(this.getDOMNode())
                this.setState({'credentialsVisible': !this.state.credentialsVisible});
            },
            handleSelectAllClick: function (event) {
                this.props.tests.invoke('set', {'checked': event.target.checked});
            },
            runTests: function () {
                var testruns = new models.TestRuns(),
                    oldTestruns = new models.TestRuns();
                this.props.testsets.each(function (testset) {
                    var selectedTestIds = _.pluck(this.props.tests.where({checked: true}), 'id');
                    if (selectedTestIds.length) {
                        var addCredentials = _.bind(function (obj) {
                            obj.ostf_os_access_creds = {
                                ostf_os_username: this.credentials.user.value,
                                ostf_os_tenant_name: this.credentials.tenant.value,
                                ostf_os_password: this.credentials.password.value
                            };
                            return obj;
                        }, this);
                        var testrunConfig = {tests: selectedTestIds};
                        if (this.props.testruns.where({testset: testset.id}).length) {
                            _.each(this.props.testruns.where({testset: testset.id}), function (testrun) {
                                _.extend(testrunConfig, addCredentials({
                                    id: testrun.id,
                                    status: 'restarted'
                                }));
                                oldTestruns.add(new models.TestRun(testrunConfig));
                            }, this);
                        } else {
                            _.extend(testrunConfig, {
                                testset: testset.id,
                                metadata: addCredentials({
                                    config: {},
                                    cluster_id: this.props.cluster.id
                                })
                            });
                            testruns.add(new models.TestRun(testrunConfig));
                        }
                    }
                }, this);
                var requests = [];
                if (testruns.length) {
                    requests.push(Backbone.sync('create', testruns));
                }
                if (oldTestruns.length) {
                    requests.push(Backbone.sync('update', oldTestruns));
                }
                $.when.apply($, requests).done(_.bind(function() {
                    this.startPolling(true);
                }, this));
            },
            render: function () {
                var disabledState = this.isLocked(),
                    hasRunningTests = !!this.props.testruns.where({status: 'running'}).length;
                this.credentials = this.props.cluster.get('settings').get('access');
                this.props.tests.each(_.bind(function(test) {
                    test.on('change:checked', _.bind(function() {
                        this.forceUpdate();
                    }, this));
                }, this));
                return (
                    <div className='wrapper'>
                        <div className='row-fluid page-sub-title'>
                            <h3 className='span6'> {$.t('cluster_page.healthcheck_tab.title')}</h3>
                            <div className='span2 ostf-controls'>
                                {!disabledState &&
                                    <div className='toggle-credentials pull-right' onClick={_.bind(this.toggleCredentials, this)}>
                                        <i className={this.state.credentialsVisible ? 'icon-minus-circle' : 'icon-plus-circle'}></i>
                                        <div>{$.t('cluster_page.healthcheck_tab.provide_credentials')}</div>
                                    </div>
                                }
                            </div>
                            <div className='span2 ostf-controls'>
                                <label className='checkbox pull-right select-all'>
                                    <input type='checkbox' className='select-all-tumbler'
                                        disabled={disabledState || hasRunningTests}
                                        checked={this.getNumberOfCheckedTests() == this.props.tests.length}
                                        onChange={_.bind(this.handleSelectAllClick, this)}
                                    />
                                    <span>&nbsp;</span>
                                    <span>{$.t('common.select_all_button')}</span>
                                </label>
                            </div>
                            <div className='span2 ostf-controls'>
                                <button className='btn btn-success pull-right action-btn run-tests-btn'
                                    disabled={disabledState || !this.getNumberOfCheckedTests()}
                                    onClick={_.bind(this.runTests, this)}
                                >
                                    {$.t('cluster_page.healthcheck_tab.run_tests_button')}
                                </button>
                                <button className='btn btn-danger pull-right action-btn stop-tests-btn hide'
                                    disabled={!hasRunningTests}
                                >
                                    {$.t('cluster_page.healthcheck_tab.stop_tests_button')}
                                </button>
                            </div>
                        </div>
                        <div>
                            {(this.props.cluster.get('status') == 'new') &&
                                <div className='row-fluid'>
                                    <div className='span12'>
                                        <div className='alert'>{$.t('cluster_page.healthcheck_tab.deploy_alert')}</div>
                                    </div>
                                </div>
                            }
                        </div>
                        <ReactCSSTransitionGroup transitionName="example">
                            <HealthcheckCredentials
                                key={this.props.cluster.get('id')}
                                visible={this.state.credentialsVisible}
                                credentials={this.credentials}
                            />
                        </ReactCSSTransitionGroup>
                        <div className='testsets'>
                            {(!this.props.tests.length) ?
                                <div className='progress-bar'>
                                    <div className='progress progress-striped progress-success active'>
                                        <div className='bar'></div>
                                    </div>
                                </div>
                                :
                                <div>
                                    {this.props.testsets.map(_.bind(function (testset) {
                                        return <TestSet
                                        key={testset.id}
                                        testset={testset}
                                        testrun={this.props.testruns.findWhere({testset: testset.id}) || new models.TestRun({testset: testset.id})}
                                        tests={new Backbone.Collection(this.props.tests.where({testset: testset.id}))}
                                        disabled={disabledState || hasRunningTests}
                                        />;
                                    }, this))}
                                </div>
                            }
                        </div>
                        <div className='alert hide error-message alert-error'>{$.t('cluster_page.healthcheck_tab.not_available_alert')}</div>
                    </div>
                );
            }
        });

var HealthcheckCredentials = React.createClass({
    componentDidUpdate: function() {
        if($(this.getDOMNode()).hasClass('credentials')) {
            $(this.getDOMNode()).fadeIn();
        }
        else {
            $(this.getDOMNode()).fadeOut();
        }
    },
    handleInputChange: function (event) {
        var target = $(event.target);
        this.props.credentials[target.attr('name')].value = target.val();
    },
    togglePassword: function (event) {
        var input = $(event.currentTarget).prev();
        if (input.attr('disabled')) {
            return;
        }
        input.attr('type', input.attr('type') == 'text' ? 'password' : 'text');
        $(event.currentTarget).find('i').toggleClass('hide');
    },
    render: function () {
        if (this.props.visible) {
            return (
                <div className='credentials hide'>
                    <div className='fieldset-group wrapper'>
                        <div className='settings-group' >
                            <div className='clearfix note'>
                                {$.t('cluster_page.healthcheck_tab.credentials_description')}
                            </div>
                            <div className='parameter-box clearfix'>
                                <div className='openstack-sub-title parameter-name'>
                                   { $.t('cluster_page.healthcheck_tab.username_label') }
                                </div>
                                <div className='parameter-control '>
                                    <input type='text' name='user'
                                    defaultValue={this.props.credentials.user.value}
                                    onChange={_.bind(this.handleInputChange, this)} />
                                </div>
                                <div className='parameter-description description'>
                                   { $.t('cluster_page.healthcheck_tab.username_description') }
                                </div>
                            </div>
                            <div className='parameter-box clearfix'>
                                <div className='openstack-sub-title parameter-name'>
                                   { $.t('cluster_page.healthcheck_tab.password_label') }
                                </div>
                                <div className='parameter-control input-append'>
                                    <input type='password' name='password' className='input-append'
                                    defaultValue={this.props.credentials.password.value}
                                    onChange={_.bind(this.handleInputChange, this)} />
                                    <span className='add-on' onClick={this.togglePassword}>
                                        <i className='icon-eye'></i>
                                        <i className='icon-eye-off hide'></i>
                                    </span>
                                </div>
                                <div className='parameter-description description'>
                                   { $.t('cluster_page.healthcheck_tab.password_description') }
                                </div>
                            </div>
                            <div className='parameter-box clearfix'>
                                <div className='openstack-sub-title parameter-name'>
                                   { $.t('cluster_page.healthcheck_tab.tenant_label') }
                                </div>
                                <div className='parameter-control'>
                                    <input type='text' name='tenant'
                                    defaultValue={this.props.credentials.tenant.value}
                                    onChange={_.bind(this.handleInputChange, this)} />
                                </div>
                                <div className='parameter-description description'>
                                   { $.t('cluster_page.healthcheck_tab.tenant_description') }
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                );
        }
        else {
            return (<div></div>);
        }
    }
});

var TestSet = React.createClass({
    mixins: [
        React.BackboneMixin('tests'),
        React.BackboneMixin('testset')
    ],
    handleTestSetCheck: function (event) {
        this.props.testset.set('checked', event.target.checked);
        this.props.tests.invoke('set', {checked: event.target.checked});
    },
    componentWillMount: function() {
        this.props.tests.each(_.bind(function(test) {
            test.on('change:checked', _.bind(function(test) {
                var checkedTests = this.props.tests.where({'checked': true});
                if (checkedTests.length == this.props.tests.length) {
                    this.props.testset.set('checked', true);
                    this.forceUpdate();
                }
                else {
                    this.props.testset.set({checked: false});
                    this.forceUpdate();
                }
            }, this));
        }, this));
    },
    render: function () {
        return (
            <div className='row-fluid'>
                <table className='table table-bordered healthcheck-table enable-selection'>
                    <thead>
                        <tr>
                            <th className='healthcheck-col-select'>
                                <div className='custom-tumbler'>
                                    <input
                                        type='checkbox'
                                        name={this.props.testset.get('name')}
                                        disabled={this.props.disabled}
                                        onChange={_.bind(this.handleTestSetCheck, this)}
                                        checked={this.props.testset.get('checked')} />
                                    <span>&nbsp;</span>
                                </div>
                            </th>
                            <th>
                                <label className='testset-name'>
                                        {this.props.testset.get('name')}
                                </label>
                            </th>
                            <th className='healthcheck-col-duration'>{$.t('cluster_page.healthcheck_tab.expected_duration')}</th>
                            <th className='healthcheck-col-duration'>{$.t('cluster_page.healthcheck_tab.actual_duration')}</th>
                            <th className='healthcheck-col-status'>{$.t('cluster_page.healthcheck_tab.status')}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {this.props.tests.map(_.bind(function (test, testIndex) {
                                var result = this.props.testrun &&
                                    _.find(this.props.testrun.get('tests'), {id: test.id});
                                var status = result && result.status || 'unknown';
                                return <Test
                                    key={test.id}
                                    test={test}
                                    result={result}
                                    testIndex={testIndex}
                                    status={status}
                                    disabled={this.props.disabled}
                                    initialState={test.get('checked')}
                                />;
                            }, this))}
                    </tbody>
                </table>
            </div>
            );
    }
});

var Test = React.createClass({
    mixins: [
        React.BackboneMixin('test')
    ],
    handleTestCheck: function (event) {
        this.props.test.set('checked', event.target.checked);
    },
    render: function () {
        var test = this.props.test,
            result = this.props.result,
            testIndex = this.props.testIndex,
            status = this.props.status,
            currentStatusClassName = 'healthcheck-status healthcheck-status-' + this.props.status;
        return (
            <tr>
                <td className='healthcheck-col-select'>
                    <div className='custom-tumbler'>
                        <input
                        type='checkbox'
                        name={test.get('name')}
                        disabled={this.props.disabled}
                        onChange={_.bind(this.handleTestCheck, this)}
                        checked={!!this.props.test.get('checked')}
                        />
                        <span>&nbsp;</span>
                    </div>
                </td>
                <td>
                    <div className='healthcheck-name'>
                        <label>{test.get('name')}</label>
                    </div>
                    {(status == 'failure' || status == 'error' || status == 'skipped') && (result && result.message) &&
                        <div className='healthcheck-msg healthcheck-status-failure'>
                            <b>{result.message}</b>
                            <br/>
                            <br/>
                            <div className='well'></div>
                        </div>
                    }
                </td>
                <td className='healthcheck-col-duration'>
                    <div className='healthcheck-duration'>{test.get('duration') || '' }</div>
                </td>
                <td className='healthcheck-col-duration'>
                    {(status != 'running' && result && _.isNumber(result.taken)) ?
                        <div className='healthcheck-duration'>{result.taken.toFixed(1) }</div>
                    :
                        <div className={currentStatusClassName}>&mdash;</div>
                    }
                </td>
                <td className = 'healthcheck-col-status'>
                    <div className={currentStatusClassName}>
                        {(status == 'success') ?
                            <i className='icon-passed'></i>
                            : (status == 'failure' || status == 'error') ?
                            <i className='icon-failed'></i>
                            : (status == 'running') ?
                            <i className='icon-process animate-spin'></i>
                            : (status == 'wait_running') ?
                            <i className='icon-clock'></i>
                            : '—'
                            }
                    </div>
                </td >
            </tr>
        )}
    });

return HealthCheckTab;

});