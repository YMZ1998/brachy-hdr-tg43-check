"""Legacy compatibility module.

Database-backed OMP integration has been removed from this project.
Use local RTPLAN DICOM files instead.
"""


def _db_removed():
    raise RuntimeError(
        "Database access has been removed. "
        "Please provide a local RTPLAN DICOM file instead."
    )


def connect_to_db():
    _db_removed()


def get_patient_cases(patient):
    _db_removed()


def get_plans_from_case(patient, case):
    _db_removed()


def get_rtplan(patient, case, plan_string="", images=False, published=False):
    _db_removed()


def write_file(data, filename="RTSTRUCT.dcm"):
    """Write binary data to file."""
    with open(filename, "wb") as file:
        file.write(data)


if __name__ == "__main__":
    print("Database features removed. Use local RTPLAN files.")
