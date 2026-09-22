resource "azurerm_subnet" "jumpbox" {
  name                 = "management"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.20.18.0/24"]
}

resource "azurerm_subnet" "bastion" {
  name                 = "AzureBastionSubnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.20.17.0/27"]
}

resource "azurerm_public_ip" "bastion" {
  name                = "${var.name_prefix}-bastion-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_bastion_host" "main" {
  name                = "${var.name_prefix}-bastion"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  tunneling_enabled   = true

  ip_configuration {
    name                 = "bastion-ip-configuration"
    subnet_id            = azurerm_subnet.bastion.id
    public_ip_address_id = azurerm_public_ip.bastion.id
  }
}

resource "azurerm_network_security_group" "jumpbox" {
  name                = "${var.name_prefix}-jumpbox-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "allow-ssh-from-bastion"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "10.20.17.0/27"
    destination_address_prefix = "10.20.18.0/24"
  }
}

resource "azurerm_network_interface" "jumpbox" {
  name                = "${var.name_prefix}-jumpbox-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.jumpbox.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_network_interface_security_group_association" "jumpbox" {
  network_interface_id      = azurerm_network_interface.jumpbox.id
  network_security_group_id = azurerm_network_security_group.jumpbox.id
}

resource "azurerm_linux_virtual_machine" "jumpbox" {
  name                            = "${var.name_prefix}-jumpbox"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  size                            = var.jumpbox_vm_size
  admin_username                  = var.jumpbox_admin_username
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.jumpbox.id]

  admin_ssh_key {
    username   = var.jumpbox_admin_username
    public_key = var.jumpbox_ssh_public_key
  }

  identity {
    type = "SystemAssigned"
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  custom_data = base64encode(<<-CLOUD_INIT
    #cloud-config
    package_update: true
    packages:
      - ca-certificates
      - curl
    runcmd:
      - bash -c 'curl -sL https://aka.ms/InstallAzureCLIDeb | bash'
      - az aks install-cli
      - install -d -m 0755 /opt/ecommerce
      - bash -c 'cat > /opt/ecommerce/connect-aks.sh <<"SCRIPT"
    #!/usr/bin/env bash
    set -euo pipefail
    az login --identity
    az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_kubernetes_cluster.main.name} --admin --overwrite-existing
    kubectl get nodes
    SCRIPT
    chmod 0755 /opt/ecommerce/connect-aks.sh'
  CLOUD_INIT
  )
}

resource "azurerm_role_assignment" "jumpbox_aks_admin" {
  scope                = azurerm_kubernetes_cluster.main.id
  role_definition_name = "Azure Kubernetes Service Cluster Admin Role"
  principal_id         = azurerm_linux_virtual_machine.jumpbox.identity[0].principal_id
}