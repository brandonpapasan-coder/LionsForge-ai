output "state_bucket_name" {
  description = "S3 bucket used for Terraform remote state."
  value       = aws_s3_bucket.terraform_state.bucket
}

output "backend_config" {
  description = "Backend configuration values for the staging stack."
  value = {
    bucket       = aws_s3_bucket.terraform_state.bucket
    key          = "aws/staging/terraform.tfstate"
    region       = var.aws_region
    encrypt      = true
    use_lockfile = true
  }
}
