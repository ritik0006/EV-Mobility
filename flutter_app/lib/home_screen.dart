import 'package:flutter/material.dart';
import 'api.dart';
import 'login_screen.dart';
import 'partner_screen.dart';
import 'renter_tabs.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int tab = 0;

  Future<void> logout() async {
    await Api.logout();
    if (!mounted) return;
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const LoginScreen()));
  }

  @override
  Widget build(BuildContext context) {
    final isPartner = Api.role == 'partner';
    final tabs = isPartner ? [const PartnerScreen()] : [const VehiclesTab(), const BookingsTab(), const KycTab()];
    return Scaffold(
      appBar: AppBar(title: Text(isPartner ? 'Fleet partner' : 'EV Rent'),
          actions: [IconButton(onPressed: logout, icon: const Icon(Icons.logout))]),
      body: tabs[tab],
      bottomNavigationBar: isPartner
          ? null
          : NavigationBar(selectedIndex: tab, onDestinationSelected: (i) => setState(() => tab = i), destinations: const [
              NavigationDestination(icon: Icon(Icons.electric_scooter), label: 'Vehicles'),
              NavigationDestination(icon: Icon(Icons.receipt_long), label: 'Bookings'),
              NavigationDestination(icon: Icon(Icons.verified_user), label: 'KYC'),
            ]),
    );
  }
}
