resource "juju_application" "karapace" {
  model_uuid = var.model_uuid
  name       = var.app_name

  charm {
    name     = "karapace-k8s"
    channel  = var.channel
    revision = var.revision
    base     = var.base
  }

  units       = var.units
  constraints = var.constraints
  config      = var.config
  trust       = true
}

# Karapace client offer
resource "juju_offer" "karapace_client" {
  model_uuid       = var.model_uuid
  application_name = juju_application.karapace.name
  endpoints        = ["karapace"]
}
