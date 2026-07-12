data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "random_password" "database" {
  length           = 32
  special          = true
  override_special = "!#$%&*+-=?@^_"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.8"

  name = var.name
  cidr = var.vpc_cidr
  azs  = local.azs

  public_subnets   = [for index, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, index)]
  private_subnets  = [for index, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, index + 10)]
  database_subnets = [for index, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, index + 20)]

  enable_nat_gateway            = true
  single_nat_gateway            = true
  enable_dns_hostnames          = true
  create_database_subnet_group = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.name
  cluster_version = "1.30"

  cluster_endpoint_public_access           = true
  enable_cluster_creator_admin_permissions = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    staging = {
      instance_types = var.eks_node_instance_types
      min_size       = var.eks_min_size
      desired_size   = var.eks_desired_size
      max_size       = var.eks_max_size
      capacity_type  = "ON_DEMAND"
    }
  }
}

resource "aws_security_group" "database" {
  name        = "${var.name}-database"
  description = "Allow PostgreSQL traffic from the EKS worker security group"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL from EKS nodes"
    protocol        = "tcp"
    from_port       = 5432
    to_port         = 5432
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

module "database" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.7"

  identifier = var.name

  engine               = "postgres"
  engine_version       = "16"
  family               = "postgres16"
  major_engine_version = "16"
  instance_class       = var.database_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true

  db_name  = var.database_name
  username = var.database_username
  password = random_password.database.result
  port     = 5432

  db_subnet_group_name   = module.vpc.database_subnet_group
  vpc_security_group_ids = [aws_security_group.database.id]

  multi_az                         = false
  publicly_accessible              = false
  backup_retention_period          = 7
  deletion_protection              = true
  skip_final_snapshot              = false
  final_snapshot_identifier_prefix = "${var.name}-final"

  performance_insights_enabled = true
  create_monitoring_role        = true
  monitoring_interval           = 60
}
