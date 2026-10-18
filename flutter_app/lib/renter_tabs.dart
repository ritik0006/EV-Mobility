import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'api.dart';

Future<String?> takePhoto() async =>
    (await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 70))?.path;

/// Generic "load a list from the API" helper widget.
class ApiList extends StatefulWidget {
  final String path;
  final Widget Function(BuildContext, Map, VoidCallback refresh) item;
  const ApiList(this.path, this.item, {super.key});
  @override
  State<ApiList> createState() => _ApiListState();
}

class _ApiListState extends State<ApiList> {
  late Future<dynamic> f = Api.get(widget.path);
  void refresh() => setState(() => f = Api.get(widget.path));
  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: () async => refresh(),
        child: FutureBuilder(
          future: f,
          builder: (c, s) {
            if (s.hasError) return Center(child: Text(s.error.toString().replaceFirst('Exception: ', '')));
            if (!s.hasData) return const Center(child: CircularProgressIndicator());
            final items = s.data as List;
            if (items.isEmpty) return ListView(children: const [Padding(padding: EdgeInsets.all(32), child: Text('Nothing here yet'))]);
            return ListView(children: [for (final i in items) widget.item(c, i as Map, refresh)]);
          },
        ),
      );
}

class VehiclesTab extends StatelessWidget {
  const VehiclesTab({super.key});

  Future<void> book(BuildContext context, Map v, VoidCallback refresh) async {
    final days = TextEditingController(text: '1');
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
              title: Text('Book ${v['name']}'),
              content: Column(mainAxisSize: MainAxisSize.min, children: [
                TextField(controller: days, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Number of days')),
                const SizedBox(height: 8),
                Text('₹${v['daily_price']}/day + ₹${v['deposit']} refundable deposit'),
              ]),
              actions: [
                TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
                FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Book')),
              ],
            ));
    if (ok != true) return;
    try {
      await Api.post('/bookings/', {'vehicle': v['id'], 'days': int.tryParse(days.text) ?? 1});
      if (context.mounted) toast(context, 'Booked! See the Bookings tab for pickup.');
      refresh();
    } catch (e) {
      if (context.mounted) toast(context, e.toString());
    }
  }

  @override
  Widget build(BuildContext context) => ApiList(
      '/vehicles/',
      (c, v, refresh) => ListTile(
            leading: const Icon(Icons.electric_scooter),
            title: Text(v['name']),
            subtitle: Text('${v['hub'] ?? ''} · ₹${v['daily_price']}/day'),
            trailing: FilledButton.tonal(onPressed: () => book(c, v, refresh), child: const Text('Book')),
          ));
}

class BookingsTab extends StatelessWidget {
  const BookingsTab({super.key});

  Future<void> handover(BuildContext context, Map b, String action, VoidCallback refresh) async {
    String qr = '';
    if (action == 'pickup') {
      // MVP: type/paste the code printed on the vehicle. Replace with mobile_scanner for real QR scanning.
      final c = TextEditingController();
      final ok = await showDialog<bool>(
          context: context,
          builder: (d) => AlertDialog(
                title: const Text('Vehicle code'),
                content: TextField(controller: c, decoration: const InputDecoration(labelText: 'Code on the vehicle')),
                actions: [TextButton(onPressed: () => Navigator.pop(d, true), child: const Text('Next: take photo'))],
              ));
      if (ok != true) return;
      qr = c.text.trim();
    }
    final photo = await takePhoto();
    if (photo == null) return;
    try {
      await Api.upload('/bookings/${b['id']}/$action/', {if (qr.isNotEmpty) 'qr_token': qr}, {'photo': photo});
      refresh();
    } catch (e) {
      if (context.mounted) toast(context, e.toString());
    }
  }

  @override
  Widget build(BuildContext context) => ApiList(
      '/bookings/',
      (c, b, refresh) => ListTile(
            title: Text('${b['vehicle_name']} · ${b['days']} day(s)'),
            subtitle: Text('₹${b['amount']} · ${b['status']}'),
            trailing: b['status'] == 'booked'
                ? FilledButton.tonal(onPressed: () => handover(c, b, 'pickup', refresh), child: const Text('Pick up'))
                : b['status'] == 'active'
                    ? FilledButton.tonal(onPressed: () => handover(c, b, 'return', refresh), child: const Text('Return'))
                    : null,
          ));
}

class KycTab extends StatefulWidget {
  const KycTab({super.key});
  @override
  State<KycTab> createState() => _KycTabState();
}

class _KycTabState extends State<KycTab> {
  String status = '...';
  String? doc, selfie;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      status = (await Api.get('/kyc/'))['status'];
    } catch (_) {}
    if (mounted) setState(() {});
  }

  Future<void> submit() async {
    try {
      await Api.upload('/kyc/', {'doc_type': 'licence'}, {'document': doc!, 'selfie': selfie!});
      await load();
    } catch (e) {
      if (mounted) toast(context, e.toString());
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(24), children: [
        Text('KYC status: $status', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        const Text('Upload your driving licence and a selfie. You can book once an admin approves it.'),
        const SizedBox(height: 16),
        OutlinedButton.icon(
            onPressed: () async { doc = await takePhoto(); setState(() {}); },
            icon: Icon(doc == null ? Icons.badge : Icons.check),
            label: const Text('Photo of licence')),
        OutlinedButton.icon(
            onPressed: () async { selfie = await takePhoto(); setState(() {}); },
            icon: Icon(selfie == null ? Icons.face : Icons.check),
            label: const Text('Selfie')),
        const SizedBox(height: 16),
        FilledButton(onPressed: doc != null && selfie != null ? submit : null, child: const Text('Submit for approval')),
      ]);
}
