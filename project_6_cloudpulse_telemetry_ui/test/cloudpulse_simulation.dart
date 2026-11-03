import '../lib/models/telemetry_node.dart';
import '../lib/state/telemetry_controller.dart';

void main() async {
  print('========================================================================');
  print('PROJECT 6: SIMULATION / DRY RUN (CLOUDPULSE SERVICE MESH MONITOR)');
  print('========================================================================\n');

  final controller = ClusterTelemetryController();

  print('[Phase 1] Discovering and Registering Multi-Region Service Nodes...');
  final nodes = [
    ServiceNode(id: 'node-us-east-1', name: 'edge-ingress-gateway', region: 'us-east-1', cluster: 'prod-us-cluster', podCount: 24),
    ServiceNode(id: 'node-us-west-2', name: 'payment-processor-svc', region: 'us-west-2', cluster: 'prod-pci-cluster', podCount: 16),
    ServiceNode(id: 'node-eu-west-1', name: 'search-catalog-engine', region: 'eu-west-1', cluster: 'prod-eu-cluster', podCount: 32),
    ServiceNode(id: 'node-ap-south-1', name: 'inventory-reconciliation', region: 'ap-south-1', cluster: 'prod-apac-cluster', podCount: 12),
  ];

  for (var n in nodes) {
    controller.registerNode(n);
    print('  + [REGISTERED] ${n.name} (${n.id}) in ${n.region} | Active Pods: ${n.podCount}');
  }

  print('\n[Phase 2] Streaming Baseline Nominal Telemetry to Cluster Nodes...');
  controller.ingestMetric('node-us-east-1', NodeMetric(cpuPct: 42.5, memoryUsageGb: 12.4, p99LatencyMs: 38.0, errorRatePct: 0.01, timestamp: DateTime.now()));
  controller.ingestMetric('node-us-west-2', NodeMetric(cpuPct: 35.0, memoryUsageGb: 8.2, p99LatencyMs: 25.0, errorRatePct: 0.00, timestamp: DateTime.now()));
  controller.ingestMetric('node-eu-west-1', NodeMetric(cpuPct: 48.0, memoryUsageGb: 18.6, p99LatencyMs: 55.0, errorRatePct: 0.02, timestamp: DateTime.now()));
  controller.ingestMetric('node-ap-south-1', NodeMetric(cpuPct: 30.0, memoryUsageGb: 6.0, p99LatencyMs: 20.0, errorRatePct: 0.00, timestamp: DateTime.now()));

  print('  -> Cluster Average CPU: ${controller.getAverageClusterCpu().toStringAsFixed(1)}%');
  print('  -> Cluster Average P99: ${controller.getAverageClusterP99().toStringAsFixed(1)} ms');
  print('  -> Total Active Alerts: ${controller.activeAlerts.length}');

  print('\n[Phase 3] Simulating Flash Crowds / Memory Leak on Search Catalog Engine (eu-west-1)...');
  controller.ingestMetric('node-eu-west-1', NodeMetric(cpuPct: 96.4, memoryUsageGb: 31.8, p99LatencyMs: 780.0, errorRatePct: 8.45, timestamp: DateTime.now()));

  final troubledNode = controller.getNode('node-eu-west-1')!;
  print('  -> Node State: ${troubledNode.name} -> Status: ${troubledNode.status.name.toUpperCase()}');
  print('  -> Triggered Alerts:');
  for (var a in controller.activeAlerts) {
    print('     * [${a.severity}] ${a.id}: ${a.message}');
  }

  print('\n[Phase 4] Automated SRE Remediating: Cordoning Degraded Node & Draining Traffic...');
  controller.cordonNode('node-eu-west-1');
  print('  -> Node ${troubledNode.name} is now: ${troubledNode.status.name.toUpperCase()}');

  print('\n[Phase 5] Post-Cordon Cluster Re-balancing:');
  for (var n in controller.allNodes) {
    final m = n.latestMetric;
    print('  - ${n.name} [${n.status.name.toUpperCase()}]: CPU ${m?.cpuPct ?? 0}% | P99 ${m?.p99LatencyMs ?? 0}ms');
  }

  print('\n========================================================================');
  print('CLOUDPULSE DRY RUN / SIMULATION COMPLETED WITH 0 ERRORS.');
  print('========================================================================');
}
