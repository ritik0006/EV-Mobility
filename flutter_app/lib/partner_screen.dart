import 'package:flutter/material.dart';
import 'api.dart';

/// Fleet partner flow: apply -> wait for admin approval -> dashboard (earnings + vehicles).
class PartnerScreen extends StatefulWidget {
  const PartnerScreen({super.key});
  @override
  State<PartnerScreen> createState() => _PartnerScreenState();
}

class _PartnerScreenState extends State<PartnerScreen> {
  Map? me;
  Map? earnings;
  List vehicles = [];
  String? error;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      me = await Api.get('/partner/me/');
      if (me!['status'] == 'approved') {
        earnings = await Api.get('/partner/earnings/');
        vehicles = await Api.get('/partner/vehicles/');
      }
    } catch (e) {
      error = e.toString();
    }
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    if (error != null) return Center(child: Text(error!));
    if (me == null) return const Center(child: CircularProgressIndicator());
    switch (me!['status']) {
      case 'none':
        return PartnerApplyForm(onDone: load);
      case 'applied':
        return RefreshIndicator(
            onRefresh: load,
            child: ListView(children: const [Padding(padding: EdgeInsets.all(32), child: Text('Application received. Our team is reviewing it. Pull down to refresh.'))]));
      case 'rejected':
        return const Center(child: Text('Your application was not approved. Please contact support.'));
    }
    return RefreshIndicator(
      onRefresh: load,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Text(me!['company_name'], style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          _stat('Your share', '₹${earnings!['partner_share']}'),
          _stat('Gross', '₹${earnings!['gross']}'),
          _stat('Active rides', '${earnings!['active_bookings']}'),
          _stat('Completed', '${earnings!['completed_bookings']}'),
        ]),
        const Divider(height: 32),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text('Your vehicles (${vehicles.length})', style: Theme.of(context).textTheme.titleMedium),
          FilledButton.tonal(onPressed: addVehicle, child: const Text('Add vehicle')),
        ]),
        for (final v in vehicles)
          ListTile(
            leading: const Icon(Icons.electric_scooter),
            title: Text('${v['name']} · ${v['reg_number']}'),
            subtitle: Text(v['approved'] == true ? v['status'] : 'Waiting for admin approval'),
          ),
      ]),
    );
  }

  Widget _stat(String label, String value) => SizedBox(
      width: 160,
      child: Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label), Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold))]))));

  Future<void> addVehicle() async {
    final name = TextEditingController(), reg = TextEditingController(), price = TextEditingController(), hub = TextEditingController();
    final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
              title: const Text('Add vehicle'),
              content: SingleChildScrollView(
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                TextField(controller: name, decoration: const InputDecoration(labelText: 'Model name')),
                TextField(controller: reg, decoration: const InputDecoration(labelText: 'Registration number')),
                TextField(controller: price, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Price per day (₹)')),
                TextField(controller: hub, decoration: const InputDecoration(labelText: 'Hub / location')),
              ])),
              actions: [
                TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
                FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Add')),
              ],
            ));
    if (ok != true) return;
    try {
      await Api.post('/partner/vehicles/', {'name': name.text, 'reg_number': reg.text, 'daily_price': price.text, 'hub': hub.text});
      await load();
    } catch (e) {
      if (mounted) toast(context, e.toString());
    }
  }
}

class PartnerApplyForm extends StatefulWidget {
  final VoidCallback onDone;
  const PartnerApplyForm({super.key, required this.onDone});
  @override
  State<PartnerApplyForm> createState() => _PartnerApplyFormState();
}

class _PartnerApplyFormState extends State<PartnerApplyForm> {
  final company = TextEditingController(), city = TextEditingController(text: 'Noida'), gst = TextEditingController(), fleet = TextEditingController();
  bool agree = false;

  Future<void> submit() async {
    try {
      await Api.post('/partner/me/', {
        'company_name': company.text.trim(),
        'city': city.text.trim(),
        'gst_number': gst.text.trim(),
        'fleet_size': int.tryParse(fleet.text) ?? 0,
        'agreement_accepted': agree,
      });
      widget.onDone();
    } catch (e) {
      if (mounted) toast(context, e.toString());
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(24), children: [
        Text('Become a fleet partner', style: Theme.of(context).textTheme.titleLarge),
        const Text('List your EVs and earn a share of every rental.'),
        TextField(controller: company, decoration: const InputDecoration(labelText: 'Company / owner name')),
        TextField(controller: city, decoration: const InputDecoration(labelText: 'City')),
        TextField(controller: gst, decoration: const InputDecoration(labelText: 'GST number (optional)')),
        TextField(controller: fleet, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Number of vehicles')),
        CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: agree,
            onChanged: (v) => setState(() => agree = v ?? false),
            title: const Text('I accept the partner agreement (revenue share, damage and theft terms)')),
        FilledButton(onPressed: submit, child: const Text('Apply')),
      ]);
}
