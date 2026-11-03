enum HealthStatus { healthy, degraded, critical, cordoned }

class NodeMetric {
  final double cpuPct;
  final double memoryUsageGb;
  final double p99LatencyMs;
  final double errorRatePct;
  final DateTime timestamp;

  NodeMetric({
    required this.cpuPct,
    required this.memoryUsageGb,
    required this.p99LatencyMs,
    required this.errorRatePct,
    required this.timestamp,
  });

  bool get isSlaBreached => p99LatencyMs > 250.0 || errorRatePct > 2.0;
}

class ServiceNode {
  final String id;
  final String name;
  final String region;
  final String cluster;
  int podCount;
  HealthStatus status;
  final List<NodeMetric> metricHistory;

  ServiceNode({
    required this.id,
    required this.name,
    required this.region,
    required this.cluster,
    this.podCount = 10,
    this.status = HealthStatus.healthy,
    List<NodeMetric>? history,
  }) : metricHistory = history ?? [];

  NodeMetric? get latestMetric => metricHistory.isNotEmpty ? metricHistory.last : null;

  void addMetric(NodeMetric metric, {int maxHistory = 50}) {
    metricHistory.add(metric);
    if (metricHistory.length > maxHistory) {
      metricHistory.removeAt(0);
    }
  }
}

class ClusterAlert {
  final String id;
  final String nodeId;
  final String severity; // INFO, WARNING, CRITICAL
  final String message;
  final DateTime timestamp;
  bool acknowledged;

  ClusterAlert({
    required this.id,
    required this.nodeId,
    required this.severity,
    required this.message,
    required this.timestamp,
    this.acknowledged = false,
  });
}
