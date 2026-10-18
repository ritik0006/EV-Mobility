import 'package:flutter/material.dart';
import 'api.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final phone = TextEditingController(), password = TextEditingController(), name = TextEditingController();
  bool register = false, partner = false, busy = false;

  Future<void> submit() async {
    setState(() => busy = true);
    try {
      final d = await Api.post(register ? '/auth/register/' : '/auth/login/', {
        'phone': phone.text.trim(),
        'password': password.text,
        if (register) 'name': name.text.trim(),
        if (register) 'role': partner ? 'partner' : 'renter',
      });
      await Api.saveSession(d);
      if (!mounted) return;
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const HomeScreen()));
    } catch (e) {
      if (mounted) toast(context, e.toString());
    }
    if (mounted) setState(() => busy = false);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: ListView(padding: const EdgeInsets.all(24), children: [
            const SizedBox(height: 40),
            Text('EV Rent', style: Theme.of(context).textTheme.headlineLarge),
            const Text('Rent a bike or earn more'),
            const SizedBox(height: 24),
            if (register) TextField(controller: name, decoration: const InputDecoration(labelText: 'Name')),
            TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Phone')),
            TextField(controller: password, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
            if (register)
              SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text("I'm a fleet partner (I own EVs)"),
                  value: partner,
                  onChanged: (v) => setState(() => partner = v)),
            const SizedBox(height: 16),
            FilledButton(onPressed: busy ? null : submit, child: Text(register ? 'Create account' : 'Log in')),
            TextButton(
                onPressed: () => setState(() => register = !register),
                child: Text(register ? 'I already have an account' : 'New here? Sign up')),
          ]),
        ),
      );
}
