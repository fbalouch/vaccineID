import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { protectedResources } from '../auth-config';
import { MatTableDataSource } from '@angular/material/table';
import { Router } from '@angular/router';
import format from 'date-fns/format';
import parse from 'date-fns/parse';

export interface SearchPatientResponse {
  patients: Patient[];
}

export interface Patient {
  id: string;
  name: string;
  surname: string;
  dob: string;
}

export interface SearchPatient {
  surname: string;
  dob: string;
}

@Component({
  selector: 'app-search-patient',
  templateUrl: './search-patient.component.html',
  styleUrls: ['./search-patient.component.css']
})
export class SearchPatientComponent implements OnInit {

  displayedColumns: string[] = ['id', 'name', 'surname', 'dob', 'profile'];
  patientSearch: SearchPatient | undefined;
  apiResponse?: SearchPatientResponse;
  dataSource = new MatTableDataSource();
  startDate = new Date(1990, 0, 1);

  constructor(
    private http: HttpClient,
    private router: Router
  ) { }

  ngOnInit() {

  }

  searchPatient(
    patientSurname: string,
    patientDOB: string
    ) {
      this.patientSearch = {
        surname: patientSurname,
        dob: format(parse(patientDOB, 'M/dd/yyyy', new Date()), 'yyyy-MM-dd')
      }
      this.http.post<SearchPatientResponse>(protectedResources.vaccineId.endpoint + 'patient/search', this.patientSearch)
        .subscribe((apiResponse: SearchPatientResponse) => {
          this.apiResponse = apiResponse;
          this.dataSource.data =  apiResponse.patients;
        })
  }

  getPatient(id: string) {
    this.router.navigateByUrl(`/get-patient?id=${id}`);
  }

}