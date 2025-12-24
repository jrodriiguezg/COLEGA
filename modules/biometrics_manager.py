import os
import json
import logging

# Configure logger
biometric_logger = logging.getLogger('biometrics')
biometric_logger.setLevel(logging.INFO)

class BiometricsManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = self.config_manager.get_all()
        # Ensure section exists
        if 'experimental' not in self.config:
            self.config['experimental'] = {
                'voice_auth_enabled': False,
                'face_auth_enabled': False
            }

    def is_voice_auth_enabled(self):
        """Check if voice authentication is globally enabled."""
        return self.config_manager.get('experimental', {}).get('voice_auth_enabled', False)

    def verify_voice(self, audio_sample):
        """
        Alpha Implementation: Always returns True if enabled, or simulates check.
        In future: Use 'sherpa-onnx' speaker identification or 'resemblyzer'.
        """
        if not self.is_voice_auth_enabled():
            return True # If disabled, we assume auth is not required (pass-through)

        biometric_logger.info("🔐 Verifying Voice Print (Alpha Simulation)...")
        # TODO: Implement real verification logic here
        # For Alpha, we just log and accept
        return True

    def toggle_voice_auth(self, enabled: bool):
        """Enable or disable voice authentication."""
        current = self.config_manager.get('experimental', {})
        current['voice_auth_enabled'] = enabled
        self.config_manager.update_config('experimental', current)
        biometric_logger.info(f"Voice Auth set to: {enabled}")
        return True
