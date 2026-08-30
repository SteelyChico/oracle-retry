import oci
import datetime
import sys

# ── Configuração ──────────────────────────────────────────────────────────────
USER_OCID      = "ocid1.user.oc1..aaaaaaaarasfgjf5pequazljjettdk6ymxykj4k5y5w6ynbsof6jz5b75fxa"
TENANCY_OCID   = "ocid1.tenancy.oc1..aaaaaaaa7ftaiwgunhkqag2s2y7tw3x22s7ltscuvh6udltggaj535s6roda"
FINGERPRINT    = "3a:65:f1:43:67:68:63:1f:eb:3e:c1:df:75:c8:fa:a7"
REGION         = "sa-saopaulo-1"
KEY_FILE       = "private_key.pem"

SUBNET_OCID    = "ocid1.subnet.oc1.sa-saopaulo-1.aaaaaaaacj2q4m2y2jxags57ootbuho3unmcjdrlizhywz3ynfeaavtwdo6a"
SSH_PUBLIC_KEY = open("ssh_key.pub").read().strip()
# ──────────────────────────────────────────────────────────────────────────────

config = {
    "user":        USER_OCID,
    "key_file":    KEY_FILE,
    "fingerprint": FINGERPRINT,
    "tenancy":     TENANCY_OCID,
    "region":      REGION,
}

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def get_image_id(compute):
    images = compute.list_images(
        compartment_id=TENANCY_OCID,
        operating_system="Canonical Ubuntu",
        operating_system_version="22.04",
        shape="VM.Standard.A1.Flex",
    ).data
    if not images:
        raise Exception("Imagem Ubuntu 22.04 ARM não encontrada!")
    return images[0].id

def try_create(compute, image_id):
    details = oci.core.models.LaunchInstanceDetails(
        compartment_id=TENANCY_OCID,
        display_name="reconftw-vm",
        availability_domain="sqXV:SA-SAOPAULO-1-AD-1",
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=2,
            memory_in_gbs=12,
        ),
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            image_id=image_id,
            source_type="image",
        ),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=SUBNET_OCID,
            assign_public_ip=True,
        ),
        metadata={
            "ssh_authorized_keys": SSH_PUBLIC_KEY,
        },
    )
    return compute.launch_instance(details).data

def main():
    compute = oci.core.ComputeClient(config)
    log("Buscando imagem Ubuntu 22.04 ARM...")
    image_id = get_image_id(compute)
    log(f"Imagem: {image_id}")
    log("Tentando criar VM...")
    try:
        instance = try_create(compute, image_id)
        log(f"✅ VM CRIADA COM SUCESSO!")
        log(f"   OCID:   {instance.id}")
        log(f"   Status: {instance.lifecycle_state}")
        sys.exit(0)
    except oci.exceptions.ServiceError as e:
        if e.status == 500 and "Out of host capacity" in str(e.message):
            log("❌ Sem capacidade. Próxima tentativa no próximo agendamento.")
            sys.exit(1)
        else:
            log(f"⚠️  Erro: {e.status} — {e.message}")
            sys.exit(1)

if __name__ == "__main__":
    main()
