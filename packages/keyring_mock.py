#!/usr/bin/env python3
"""Mock keyring module for compatibility."""

def get_password(service, username):
    """Return None as password."""
    return None

def set_password(service, username, password):
    """No-op."""
    pass

# Mock classes
class Keyring:
    def get_password(self, service, username):
        return None
    
    def set_password(self, service, username, password):
        pass

# Create default keyring
_keyring = Keyring()

# Module-level functions
def get_keyring():
    return _keyring
