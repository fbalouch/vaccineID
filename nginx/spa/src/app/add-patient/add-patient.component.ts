import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { protectedResources } from '../auth-config';
import { Router } from '@angular/router';
import format from 'date-fns/format';
import parse from 'date-fns/parse';

export interface AddPatientResponse {
  id: string;
}

export interface AddPatient {
  name: string;
  surname: string;
  dob: string;
}

@Component({
  selector: 'app-add-patient',
  templateUrl: './add-patient.component.html',
  styleUrls: ['./add-patient.component.css']
})

export class AddPatientComponent implements OnInit {

  patientData: AddPatient | undefined;
  apiResponse?: AddPatientResponse;
  startDate = new Date(1990, 0, 1);

  constructor(
    private http: HttpClient,
    private router: Router
  ) { }

  ngOnInit() {
  }

  addPatient(
    patientName: string, 
    patientSurname: string,
    patientDOB: string
    ) {
      this.patientData = {
        name: patientName,
        surname: patientSurname,
        dob: format(parse(patientDOB, 'M/dd/yyyy', new Date()), 'yyyy-MM-dd')
      }
      this.http.post<AddPatientResponse>(protectedResources.vaccineId.endpoint + 'patient', this.patientData)
        .subscribe((apiResponse: AddPatientResponse) => {
          this.apiResponse = apiResponse;
        })
  }

  getPatient() {
    let id = this.apiResponse?.id
    this.router.navigateByUrl(`/get-patient?id=${id}`);
  }

}