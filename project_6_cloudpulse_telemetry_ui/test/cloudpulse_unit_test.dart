import 'package:test/test.dart';
import '../lib/models/telemetry_node.dart';
import '../lib/state/telemetry_controller.dart';

void main() {
  group('CloudPulse Telemetry Controller Unit Tests', () {
    late ClusterTelemetryController controller;

    setUp(() {
      controller = ClusterTelemetryController();
    });

    test('Register and look up service nodes', () {
      final node = ServiceNode(id: 'node-us-east-1', name: 'api-gateway-01', region: 'us-east-1', cluster: 'k8s-prod');
      controller.registerNode(node);

      final retrieved = controller.getNode('node-us-east-1');
      expect(retrieved, isNotNull);
      expect(retrieved!.name, equals('api-gateway-01'));
      expect(retrieved.status, equals(HealthStatus.healthy));
    });

    test('Sliding window metric history limits buffer size', () {
      final node = ServiceNode(id: 'node-eu-1', name: 'auth-service', region: 'eu-central-1', cluster: 'k8s-prod');
      controller.registerNode(node);

      for (int i = 0; i < 60; i++) {
        controller.ingestMetric(
          'node-eu-1',
          NodeMetric(cpuPct: 40.0, memoryUsageGb: 4.0, p99LatencyMs: 45.0, errorRatePct: 0.05, timestamp: DateTime.now()),
        );
      }

      // Max history buffer is 50
      expect(node.metricHistory.length, equals(50));
    });

    test('Health transitions from healthy to degraded to critical based on thresholds', () {
      final node = ServiceNode(id: 'node-db', name: 'postgres-replica', region: 'us-west-2', cluster: 'k8s-data');
      controller.registerNode(node);

      // 1. Ingest normal metrics -> healthy
      controller.ingestMetric(
        'node-db',
        NodeMetric(cpuPct: 35.0, memoryUsageGb: 8.0, p99LatencyMs: 30.0, errorRatePct: 0.0, timestamp: DateTime.now()),
      );
      expect(node.status, equals(HealthStatus.healthy));

      // 2. High latency spike -> degraded
      controller.ingestMetric(
        'node-db',
        NodeMetric(cpuPct: 50.0, memoryUsageGb: 8.5, p99LatencyMs: 280.0, errorRatePct: 0.1, timestamp: DateTime.now()),
      );
      expect(node.status, equals(HealthStatus.degraded));
      expect(controller.activeAlerts.length, equals(1));
      expect(controller.activeAlerts.first.severity, equals('WARNING'));

      // 3. CPU >= 90% and error rate >= 5% -> critical
      controller.ingestMetric(
        'node-db',
        NodeMetric(cpuPct: 94.0, memoryUsageGb: 15.8, p99LatencyMs: 650.0, errorRatePct: 7.5, timestamp: DateTime.now()),
      );
      expect(node.status, equals(HealthStatus.critical));
      expect(controller.activeAlerts.length, equals(2));
      expect(controller.activeAlerts.last.severity, equals('CRITICAL'));
    });

    test('Manual cordoning locks node in cordoned state', () {
      final node = ServiceNode(id: 'node-worker', name: 'payment-worker', region: 'us-east-1', cluster: 'k8s-prod');
      controller.registerNode(node);

      controller.cordonNode('node-worker');
      expect(node.status, equals(HealthStatus.cordoned));

      // Ingesting metrics should not alter cordoned status
      controller.ingestMetric(
        'node-worker',
        NodeMetric(cpuPct: 20.0, memoryUsageGb: 2.0, p99LatencyMs: 10.0, errorRatePct: 0.0, timestamp: DateTime.now()),
      );
      expect(node.status, equals(HealthStatus.cordoned));

      controller.uncordonNode('node-worker');
      expect(node.status, equals(HealthStatus.healthy));
    });

    test('Cluster aggregates compute average CPU and P99 latency across fleet', () {
      final n1 = ServiceNode(id: 'n1', name: 'node-1', region: 'us-east', cluster: 'c1');
      final n2 = ServiceNode(id: 'n2', name: 'node-2', region: 'us-east', cluster: 'c1');
      controller.registerNode(n1);
      controller.registerNode(n2);

      controller.ingestMetric('n1', NodeMetric(cpuPct: 40.0, memoryUsageGb: 4.0, p99LatencyMs: 100.0, errorRatePct: 0.0, timestamp: DateTime.now()));
      controller.ingestMetric('n2', NodeMetric(cpuPct: 60.0, memoryUsageGb: 6.0, p99LatencyMs: 200.0, errorRatePct: 0.0, timestamp: DateTime.now()));

      expect(controller.getAverageClusterCpu(), closeTo(50.0, 0.01));
      expect(controller.getAverageClusterP99(), closeTo(150.0, 0.01));
    });
  });
}
