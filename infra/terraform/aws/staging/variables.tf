variable "aws_region" {
  description = "AWS region for the staging environment."
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Resource name prefix."
  type        = string
  default     = "onyxmane-staging"
}

variable "vpc_cidr" {
  description = "CIDR block for the staging VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "allowed_ingress_cidrs" {
  description = "CIDRs permitted to reach the staging ALB. Narrow this where possible."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ecs_cluster_name" {
  type    = string
  default = "onyxmane-staging"
}

variable "backend_service_name" {
  type    = string
  default = "onyxmane-staging-backend"
}

variable "frontend_service_name" {
  type    = string
  default = "onyxmane-staging-frontend"
}

variable "backend_container_name" {
  type    = string
  default = "backend"
}

variable "frontend_container_name" {
  type    = string
  default = "frontend"
}

variable "backend_ecr_repository_name" {
  type    = string
  default = "onyxmane-staging-backend"
}

variable "frontend_ecr_repository_name" {
  type    = string
  default = "onyxmane-staging-frontend"
}

variable "alb_name" {
  type    = string
  default = "onyxmane-staging-alb"
}

variable "backend_target_group_name" {
  type    = string
  default = "onyxmane-stg-backend-tg"
}

variable "frontend_target_group_name" {
  type    = string
  default = "onyxmane-stg-frontend-tg"
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS. Leave empty only during initial infrastructure bootstrap."
  type        = string
  default     = ""
}

variable "bootstrap_backend_image" {
  description = "Initial backend container image URI used to create the ECS service. Subsequent releases are replaced by the staging ECS workflow."
  type        = string
}

variable "bootstrap_frontend_image" {
  description = "Initial frontend container image URI used to create the ECS service. Subsequent releases are replaced by the staging ECS workflow."
  type        = string
}

variable "backend_container_port" {
  type    = number
  default = 8000
}

variable "frontend_container_port" {
  type    = number
  default = 3000
}

variable "backend_health_check_path" {
  type    = string
  default = "/health"
}

variable "frontend_health_check_path" {
  type    = string
  default = "/login"
}

variable "backend_path_patterns" {
  description = "ALB path patterns routed to the backend service."
  type        = list(string)
  default     = ["/api/*", "/health", "/ready"]
}

variable "backend_cpu" {
  type    = number
  default = 512
}

variable "backend_memory" {
  type    = number
  default = 1024
}

variable "frontend_cpu" {
  type    = number
  default = 256
}

variable "frontend_memory" {
  type    = number
  default = 512
}

variable "backend_desired_count" {
  type    = number
  default = 1
}

variable "frontend_desired_count" {
  type    = number
  default = 1
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "backend_secrets" {
  description = "Map of backend container environment variable names to Secrets Manager or SSM parameter ARNs. Secret values must never be committed."
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "database_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "onyxmane"
}

variable "database_username" {
  description = "PostgreSQL administrator username."
  type        = string
  default     = "onyxmane_admin"
}

variable "database_instance_class" {
  description = "RDS instance class for staging."
  type        = string
  default     = "db.t4g.micro"
}
