# Diagramme de classes - Outils

```mermaid
classDiagram
%% source: app/tools
class ToolGateway {
  +workspace_root
  +read_file(path)
  +write_file(path, content)
  +execute_bash(command)
}
class ShadowDockerExecutor {
  +run_in_container(command)
}
class KineticShadowNetns {
  +isolate_network()
}
class DesignSystemBridge {
  +shadcn_home
  +list_components()
  +search_components(query)
  +read_component_code(component_name)
  +package_design_kit_bundle()
  +export_to_telegram(telegram_vault)
}
```
