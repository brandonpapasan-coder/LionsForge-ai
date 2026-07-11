variable "aws_region" {
  description = "AWS region for the staging environment."
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Resource name prefix."
  type        = string
  default     = "lionsforge-staging"
}

variable "vpc_cidr" {
  description = "CIDR block for the staging VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "database_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "lionsforge"
}

variable "database_username" {
  description = "PostgreSQL administrator username."
  type        = string
  default     = "lionsforge_admin"
}

variable "database_instance_class" {
  description = "RDS instance class for staging."
  type        = string
  default     = "db.t4g.micro"
}

variable "eks_node_instance_types" {
  description = "EC2 instance types used by the EKS managed node group."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "eks_min_size" {
  type    = number
  default = 1
}

variable "eks_desired_size" {
  type    = number
  default = 2
}

variable "eks_max_size" {
  type    = number
  default = 3
}
