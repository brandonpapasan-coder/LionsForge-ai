output "aws_region" {
  value = var.aws_region
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "backend_service_name" {
  value = aws_ecs_service.backend.name
}

output "frontend_service_name" {
  value = aws_ecs_service.frontend.name
}

output "backend_ecr_repository" {
  value = aws_ecr_repository.backend.name
}

output "frontend_ecr_repository" {
  value = aws_ecr_repository.frontend.name
}

output "alb_dns_name" {
  value = aws_lb.this.dns_name
}

output "backend_target_group_arn" {
  value = aws_lb_target_group.backend.arn
}

output "frontend_target_group_arn" {
  value = aws_lb_target_group.frontend.arn
}

output "task_execution_role_arn" {
  value = aws_iam_role.task_execution.arn
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
