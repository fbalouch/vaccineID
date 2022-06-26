import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpParams} from '@angular/common/http';
import { protectedResources } from '../auth-config';
import { ActivatedRoute } from '@angular/router';
import { MatTableDataSource } from '@angular/material/table';
import format from 'date-fns/format';
import parse from 'date-fns/parse';

export interface AddPatientRecordResponse {
  id: string;
}

export interface GetPatientResponse {
  id: string;
  name: string;
  surname: string;
  dob: string;
  immunizations: ImmunizationRecord[]
}

export interface ImmunizationRecord {
    name: string;
    manufacturer: string;
    lot: string;
    provider: string;
    date: string;
}

export interface AddPatientRecord {
  name: string;
  manufacturer: string;
  lot: string;
  provider: string;
  date: string;
}

@Component({
  selector: 'app-get-patient',
  templateUrl: './get-patient.component.html',
  styleUrls: ['./get-patient.component.css']
})

export class GetPatientComponent implements OnInit {
  displayedColumns = ['name', 'manufacturer', 'lot', 'provider', 'date'];
  apiResponse?: GetPatientResponse;
  dataSource = new MatTableDataSource();
  patientRecord: AddPatientRecord | undefined;
  showRecords: boolean = true;
  recordResponse?: AddPatientRecordResponse;

  constructor(
    private http: HttpClient,
    private route: ActivatedRoute,
  ) { }

  ngOnInit() {
    let id = this.route.snapshot.queryParamMap.get('id');
    if (id == null ) {
      console.error('missing patient id param')
    }
    else {
      this.getPatient(id)
    }
  }

  getPatient(id: string) {
    this.http.get<GetPatientResponse>(protectedResources.vaccineId.endpoint + 'patient', 
      {params: new HttpParams().set('id', id)})
        .subscribe((apiResponse: GetPatientResponse) => {
          this.apiResponse = apiResponse;
          this.dataSource.data = apiResponse.immunizations;
        });
  }

  createRecord() {
    this.showRecords = false;
  }

  addRecord(
    recordName: string,
    recordManufacturer: string,
    recordLot: string,
    recordProvider: string,
    recordDate: string
    ) {
      this.patientRecord = {
        name: recordName,
        manufacturer: recordManufacturer,
        lot: recordLot,
        provider: recordProvider,
        date: format(parse(recordDate, 'M/dd/yyyy', new Date()), 'yyyy-MM-dd')
      }
      let id = this.route.snapshot.queryParamMap.get('id');
      
      this.http.post<AddPatientRecordResponse>(protectedResources.vaccineId.endpoint + `patient/${id}/record`, this.patientRecord)
        .subscribe((addRecordResponse: AddPatientRecordResponse) => {
          this.getPatient(addRecordResponse.id);
        });
      
    }

}