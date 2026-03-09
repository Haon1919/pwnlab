import docker
import logging
from typing import Dict, List, Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)

# Default security options for target containers
TARGET_SECURITY_DEFAULTS = {
    "cap_drop": ["ALL"],
    "security_opt": ["no-new-privileges:true"],
    "mem_limit": "512m",
    "cpu_quota": 50000,
    "network_mode": "none",  # overridden when attaching to session network
}

class DockerManager:
    def __init__(self):
        self._client: Optional[docker.DockerClient] = None

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def create_network(self, network_name: str, subnet: str, internal: bool = True) -> str:
        """Create an isolated Docker bridge network for a session."""
        try:
            ipam_pool = docker.types.IPAMPool(subnet=subnet)
            ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
            network = self.client.networks.create(
                name=network_name,
                driver="bridge",
                internal=internal,
                ipam=ipam_config,
                labels={"blaqliq": "true", "managed": "true"},
            )
            logger.info(f"Created network {network_name} with subnet {subnet}")
            return network.id
        except docker.errors.APIError as e:
            logger.error(f"Failed to create network {network_name}: {e}")
            raise

    def run_target(
        self,
        image: str,
        container_name: str,
        network_name: str,
        ip_address: str,
        mem_limit: str = "512m",
        cpu_quota: int = 50000,
        environment: Optional[Dict[str, str]] = None,
        extra_hosts: Optional[Dict[str, str]] = None,
    ) -> str:
        """Run a target container with security hardening."""
        if image not in settings.allowed_images_list:
            raise ValueError(f"Image {image} not in allowed images whitelist")

        try:
            container = self.client.containers.run(
                image=image,
                name=container_name,
                detach=True,
                remove=False,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                mem_limit=mem_limit,
                cpu_quota=cpu_quota,
                network=network_name,
                labels={"blaqliq": "true", "role": "target"},
                environment=environment or {},
                extra_hosts=extra_hosts or {},
            )
            # Assign specific IP to container on network
            network = self.client.networks.get(network_name)
            network.disconnect(container)
            network.connect(container, ipv4_address=ip_address)
            logger.info(f"Started target container {container_name} ({image}) at {ip_address}")
            return container.id
        except docker.errors.APIError as e:
            logger.error(f"Failed to run target container {container_name}: {e}")
            raise

    def run_attacker(
        self,
        image: str,
        container_name: str,
        network_name: str,
        ip_address: str,
        environment: Optional[Dict[str, str]] = None,
        kali: bool = False,
        net_admin: bool = False,
    ) -> str:
        """Run attacker container with optional kali and NET_ADMIN capabilities."""
        caps = []
        if net_admin:
            caps.append("NET_ADMIN")

        try:
            container = self.client.containers.run(
                image=image,
                name=container_name,
                detach=True,
                remove=False,
                tty=True,
                stdin_open=True,
                cap_add=caps if caps else None,
                mem_limit="1g",
                network=network_name,
                labels={"blaqliq": "true", "role": "attacker"},
                environment=environment or {},
            )
            network = self.client.networks.get(network_name)
            network.disconnect(container)
            network.connect(container, ipv4_address=ip_address)
            logger.info(f"Started attacker container {container_name} at {ip_address}")
            return container.id
        except docker.errors.APIError as e:
            logger.error(f"Failed to run attacker container {container_name}: {e}")
            raise

    def run_wargame_sidecar(
        self,
        container_name: str,
        network_name: str,
        events_volume: str,
        session_id: str,
        target_container_id: str,
    ) -> str:
        """Run wargame detection sidecar with NET_ADMIN capability."""
        try:
            container = self.client.containers.run(
                image=settings.BLAQLIQ_WARGAME_SIDECAR_IMAGE,
                name=container_name,
                detach=True,
                remove=False,
                cap_add=["NET_ADMIN", "AUDIT_CONTROL", "AUDIT_READ"],
                network_mode=f"container:{target_container_id}",
                pid_mode=f"container:{target_container_id}",
                volumes_from=[target_container_id],
                labels={"blaqliq": "true", "role": "sidecar"},
                environment={"SESSION_ID": session_id},
                volumes={events_volume: {"bind": "/events", "mode": "rw"}},
            )
            logger.info(f"Started wargame sidecar {container_name}")
            return container.id
        except docker.errors.APIError as e:
            logger.error(f"Failed to run wargame sidecar {container_name}: {e}")
            raise

    def create_volume(self, volume_name: str) -> str:
        """Create a named Docker volume."""
        volume = self.client.volumes.create(
            name=volume_name,
            labels={"blaqliq": "true"},
        )
        return volume.name

    def get_container_status(self, container_id: str) -> Dict[str, Any]:
        """Get status info for a container."""
        try:
            container = self.client.containers.get(container_id)
            return {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
            }
        except docker.errors.NotFound:
            return {"id": container_id, "status": "not_found"}

    def stop_container(self, container_id: str, timeout: int = 10):
        """Stop and remove a container."""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            container.remove(force=True)
            logger.info(f"Stopped and removed container {container_id}")
        except docker.errors.NotFound:
            logger.warning(f"Container {container_id} not found during teardown")
        except docker.errors.APIError as e:
            logger.error(f"Error stopping container {container_id}: {e}")

    def teardown_session(self, container_ids: List[str], network_name: str, volume_name: Optional[str] = None):
        """Stop all containers and remove network for a session."""
        for cid in container_ids:
            self.stop_container(cid)

        try:
            network = self.client.networks.get(network_name)
            network.remove()
            logger.info(f"Removed network {network_name}")
        except docker.errors.NotFound:
            logger.warning(f"Network {network_name} not found during teardown")
        except docker.errors.APIError as e:
            logger.error(f"Error removing network {network_name}: {e}")

        if volume_name:
            try:
                volume = self.client.volumes.get(volume_name)
                volume.remove()
                logger.info(f"Removed volume {volume_name}")
            except docker.errors.NotFound:
                pass

    def cleanup_stale_sessions(self, active_container_ids: List[str]):
        """Remove any blaqliq containers not in the active list."""
        containers = self.client.containers.list(filters={"label": "blaqliq=true"})
        for c in containers:
            if c.id not in active_container_ids:
                logger.info(f"Cleaning up stale container {c.name}")
                self.stop_container(c.id)

    def cleanup_orphaned_resources(self, active_session_ids: List[str]):
        """Remove any blaqliq networks and volumes not associated with active sessions."""
        # Cleanup networks
        networks = self.client.networks.list(filters={"label": "blaqliq=true"})
        for net in networks:
            # Network names are like blaqliq-{session_id[:8]}
            is_active = any(net.name.endswith(sid[:8]) for sid in active_session_ids)
            if not is_active:
                logger.info(f"Cleaning up orphaned network {net.name}")
                try:
                    net.remove()
                except docker.errors.APIError as e:
                    logger.error(f"Error removing orphaned network {net.name}: {e}")

        # Cleanup volumes
        volumes = self.client.volumes.list(filters={"label": "blaqliq=true"})
        for vol in volumes:
            # Volume names are like blaqliq-events-{session_id[:8]}
            is_active = any(vol.name.endswith(sid[:8]) for sid in active_session_ids)
            if not is_active:
                logger.info(f"Cleaning up orphaned volume {vol.name}")
                try:
                    vol.remove()
                except docker.errors.APIError as e:
                    logger.error(f"Error removing orphaned volume {vol.name}: {e}")


docker_manager = DockerManager()
