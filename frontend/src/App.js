import React from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import DecisionTree from './components/DecisionTree';
import CertificateRequest from './components/CertificateRequest';
import Dashboard from './components/Dashboard';
import Navigation from './components/Navigation';

const App = () => {
  return (
    <Router>
      <Navigation />
      <Switch>
        <Route path="/decision-tree" component={DecisionTree} />
        <Route path="/certificate-request" component={CertificateRequest} />
        <Route path="/dashboard" component={Dashboard} />
      </Switch>
    </Router>
  );
};

export default App;