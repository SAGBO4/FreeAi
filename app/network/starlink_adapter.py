class StarlinkAdapter:
    """
    Stub prêt pour intégration Starlink.
    Si l'utilisateur acquiert une parabole Starlink, elle expose une API gRPC
    locale sur 192.168.100.1:9200. Activer avec:
    - pip install starlink-grpc-tools
    - Configurer STARLINK_IP dans .env
    """
    async def get_signal_quality(self) -> float | None:
        """Retourne qualité signal 0-1 si Starlink configuré, None sinon."""
        return None  # À implémenter quand hardware disponible
    
    async def get_visible_satellites(self) -> int:
        """Nombre de satellites Starlink visibles."""
        return 0
