import '../models/telemetry_node.dart';

class ClusterTelemetryController {
  final Map<String, ServiceNode> _nodes = {};
  final List<ClusterAlert> _alerts = [];
  int _alertCounter = 1;

  List<ServiceNode> get allNodes => _nodes.values.toList();
  List<ClusterAlert> get activeAlerts => _alerts.where((a) => !a.acknowledged).toList();

  void registerNode(ServiceNode node) {
    _nodes[node.id] = node;
  }

  ServiceNode? getNode(String id) => _nodes[id];

  void ingestMetric(String nodeId, NodeMetric metric) {
    final node = _nodes[nodeId];
    if (node == null) return;

    node.addMetric(metric);

    // If node is manually cordoned, preserve cordoned state
    if (node.status == HealthStatus.cordoned) {
      return;
    }

    // Health state evaluation
    if (metric.cpuPct >= 90.0 || metric.p99LatencyMs >= 500.0 || metric.errorRatePct >= 5.0) {
      node.status = HealthStatus.critical;
      _createAlert(
        nodeId: node.id,
        severity: 'CRITICAL',
        message: 'Node ${node.name} in ${node.region} critical: CPU ${metric.cpuPct.toStringAsFixed(1)}%, P99 ${metric.p99LatencyMs.toStringAsFixed(1)}ms, Error ${metric.errorRatePct.toStringAsFixed(2)}%',
      );
    } else if (metric.cpuPct >= 75.0 || metric.p99LatencyMs >= 250.0 || metric.errorRatePct >= 1.5) {
      node.status = HealthStatus.degraded;
      _createAlert(
        nodeId: node.id,
        severity: 'WARNING',
        message: 'Node ${node.name} degraded SLA threshold exceeded',
      );
    } else {
      node.status = HealthStatus.healthy;
    }
  }

  void _createAlert({required String nodeId, required String severity, required String message}) {
    // Avoid spamming duplicate unresolved alerts for the same node and severity
    final existing = _alerts.any((a) => a.nodeId == nodeId && a.severity == severity && !a.acknowledged);
    if (!existing) {
      _alerts.add(ClusterAlert(
        id: 'ALT-${_alertCounter++}',
        nodeId: nodeId,
        severity: severity,
        message: message,
        timestamp: DateTime.now(),
      ));
    }
  }

  void cordonNode(String nodeId) {
    final node = _nodes[nodeId];
    if (node != null) {
      node.status = HealthStatus.cordoned;
      _createAlert(
        nodeId: nodeId,
        severity: 'INFO',
        message: 'Node ${node.name} has been manually cordoned and traffic drained.',
      );
    }
  }

  void uncordonNode(String nodeId) {
    final node = _nodes[nodeId];
    if (node != null) {
      node.status = HealthStatus.healthy;
    }
  }

  void acknowledgeAlert(String alertId) {
    final alert = _alerts.firstWhere((a) => a.id == alertId);
    alert.acknowledged = true;
  }

  double getAverageClusterCpu() {
    final active = _nodes.values.where((n) => n.latestMetric != null).toList();
    if (active.isEmpty) return 0.0;
    return active.fold(0.0, (sum, n) => sum + n.latestMetric!.cpuPct) / active.length;
  }

  double getAverageClusterP99() {
    final active = _nodes.values.where((n) => n.latestMetric != null).toList();
    if (active.isEmpty) return 0.0;
    return active.fold(0.0, (sum, n) => sum + n.latestMetric!.p99LatencyMs) / active.length;
  }
}
