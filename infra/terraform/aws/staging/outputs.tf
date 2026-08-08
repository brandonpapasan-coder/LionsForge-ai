output "aws_region" {
  value = var.aws_region
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "configure_kubectl_command" {
  value = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "database_host" {
  value     = module.database.db_instance_address
  sensitive = true
}

output "database_port" {
  value = module.database.db_instance_port
}

output "database_name" {
  value = var.database_name
}

output "database_username" {
  value     = var.database_username
  sensitive = true
}
