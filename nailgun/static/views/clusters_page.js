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

import $ from 'jquery';
import _ from 'underscore';
import i18n from 'i18n';
import React from 'react';
import utils from 'utils';
import models from 'models';
import dispatcher from 'dispatcher';
import {backboneMixin, pollingMixin} from 'component_mixins';
import CreateClusterWizard from 'views/wizard';

var ClustersPage, ClusterList, Cluster;

ClustersPage = React.createClass({
  statics: {
    title: i18n('clusters_page.title'),
    navbarActiveElement: 'clusters',
    breadcrumbsPath: [['home', '#'], 'environments'],
    fetchData() {
      var clusters = new models.Clusters();
      var nodes = new models.Nodes();
      var tasks = new models.Tasks();
      return $.when(clusters.fetch(), nodes.fetch(), tasks.fetch()).done(() => {
        clusters.each((cluster) => {
          cluster.set('nodes', new models.Nodes(nodes.where({cluster: cluster.id})));
          cluster.set('tasks', new models.Tasks(tasks.where({cluster: cluster.id})));
        }, this);
      }).then(() => ({clusters: clusters}));
    }
  },
  render() {
    return (
      <div className='clusters-page'>
        <div className='page-title'>
          <h1 className='title'>{i18n('clusters_page.title')}</h1>
        </div>
        <ClusterList clusters={this.props.clusters} />
      </div>
    );
  }
});

ClusterList = React.createClass({
  mixins: [backboneMixin('clusters')],
  createCluster() {
    CreateClusterWizard.show({clusters: this.props.clusters, modalClass: 'wizard', backdrop: 'static'});
  },
  render() {
    return (
      <div className='row'>
        {this.props.clusters.map((cluster) => {
          return <Cluster key={cluster.id} cluster={cluster} />;
        }, this)}
        <div key='create-cluster' className='col-xs-3'>
          <button className='btn-link create-cluster' onClick={this.createCluster}>
            <span>{i18n('clusters_page.create_cluster_text')}</span>
          </button>
        </div>
      </div>
    );
  }
});

Cluster = React.createClass({
  mixins: [
    backboneMixin('cluster'),
    backboneMixin({modelOrCollection(props) {
      return props.cluster.get('nodes');
    }}),
    backboneMixin({modelOrCollection(props) {
      return props.cluster.get('tasks');
    }}),
    backboneMixin({modelOrCollection(props) {
      return props.cluster.task({group: 'deployment', active: true});
    }}),
    pollingMixin(3)
  ],
  shouldDataBeFetched() {
    return this.props.cluster.task({group: 'deployment', active: true}) ||
      this.props.cluster.task({name: 'cluster_deletion', active: true}) ||
      this.props.cluster.task({name: 'cluster_deletion', status: 'ready'});
  },
  fetchData() {
    var request;
    var requests = [];
    var deletionTask = this.props.cluster.task('cluster_deletion');
    if (deletionTask) {
      request = deletionTask.fetch();
      request.fail((response) => {
        if (response.status == 404) {
          this.props.cluster.collection.remove(this.props.cluster);
          dispatcher.trigger('updateNodeStats');
        }
      });
      requests.push(request);
    }
    var deploymentTask = this.props.cluster.task({group: 'deployment', active: true});
    if (deploymentTask) {
      request = deploymentTask.fetch();
      request.done(() => {
        if (deploymentTask.match({active: false})) {
          this.props.cluster.fetch();
          dispatcher.trigger('updateNodeStats');
        }
      });
      requests.push(request);
    }
    return $.when(...requests);
  },
  render() {
    var cluster = this.props.cluster;
    var status = cluster.get('status');
    var nodes = cluster.get('nodes');
    var isClusterDeleted = !!cluster.task({name: 'cluster_deletion', active: true}) || !!cluster.task({name: 'cluster_deletion', status: 'ready'});
    var deploymentTask = cluster.task({group: 'deployment', active: true});
    var Tag = isClusterDeleted ? 'div' : 'a';
    return (
      <div className='col-xs-3'>
        <Tag
          className={utils.classNames({
            clusterbox: true,
            'cluster-disabled': isClusterDeleted
          })}
          href={isClusterDeleted ? null : '#cluster/' + cluster.id}
        >
          <div className='name'>{cluster.get('name')}</div>
          <div className='tech-info'>
            <div key='nodes-title' className='item'>{i18n('clusters_page.cluster_hardware_nodes')}</div>
            <div key='nodes-value' className='value'>{nodes.length}</div>
            {!!nodes.length && [
              <div key='cpu-title' className='item'>{i18n('clusters_page.cluster_hardware_cpu')}</div>,
              <div key='cpu-value' className='value'>{nodes.resources('cores')} ({nodes.resources('ht_cores')})</div>,
              <div key='hdd-title' className='item'>{i18n('clusters_page.cluster_hardware_hdd')}</div>,
              <div key='hdd-value' className='value'>{nodes.resources('hdd') ? utils.showDiskSize(nodes.resources('hdd')) : '?GB'}</div>,
              <div key='ram-title' className='item'>{i18n('clusters_page.cluster_hardware_ram')}</div>,
              <div key='ram-value' className='value'>{nodes.resources('ram') ? utils.showMemorySize(nodes.resources('ram')) : '?GB'}</div>
            ]}
          </div>
          <div className='status text-info'>
            {deploymentTask ?
              <div className='progress'>
                <div
                  className={utils.classNames({
                    'progress-bar': true,
                    'progress-bar-warning': _.contains(['stop_deployment', 'reset_environment'], deploymentTask.get('name'))
                  })}
                  style={{width: (deploymentTask.get('progress') > 3 ? deploymentTask.get('progress') : 3) + '%'}}
                ></div>
              </div>
            :
              <span className={utils.classNames({
                'text-danger': status == 'error' || status == 'update_error',
                'text-success': status == 'operational'
              })}>
                {i18n('cluster.status.' + status, {defaultValue: status})}
              </span>
            }
          </div>
        </Tag>
      </div>
    );
  }
});

export default ClustersPage;
