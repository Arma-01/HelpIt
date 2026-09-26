/**
 * Mock ERP Dataset
 * Contains fictional demo data for 60 students, subjects, classes, and initial attendance history.
 * DO NOT USE REAL STUDENT INFORMATION.
 */

const MOCK_DATA = {
  institution: {
    name: "Vidyapeeth Institute of Technology & Management",
    shortName: "VITM Academic Portal",
    code: "VITM-804",
    academicYear: "2026-2027",
    currentSemester: "Even Semester",
  },

  currentUser: {
    id: "FAC-1042",
    name: "Prof. Rajesh Sharma",
    designation: "Assistant Professor",
    department: "Department of Computer Applications",
    email: "rajesh.sharma@vitm.ac.in",
    avatar: "RS",
  },

  classes: [
    { id: "BCA-2", name: "BCA - 2nd Year (Semester IV)", section: "Section A", defaultSubject: "CS-401" },
    { id: "BCA-3", name: "BCA - 3rd Year (Semester VI)", section: "Section B", defaultSubject: "CS-602" },
    { id: "MCA-1", name: "MCA - 1st Year (Semester II)", section: "Section A", defaultSubject: "MCA-203" },
  ],

  subjects: [
    { code: "CS-401", name: "Database Management Systems", classId: "BCA-2", credits: 4, type: "Theory" },
    { code: "CS-402", name: "Operating Systems & Shell Scripting", classId: "BCA-2", credits: 4, type: "Theory" },
    { code: "CS-403", name: "Object Oriented Programming via Java", classId: "BCA-2", credits: 3, type: "Theory" },
    { code: "CS-404", name: "Computer Networks & Security", classId: "BCA-2", credits: 3, type: "Theory" },
  ],

  /**
   * 60 Demo Students:
   * Carefully constructed with realistic names, unique roll numbers, unique student IDs,
   * and deliberate name overlaps (e.g. Aman Kumar vs Aman Sharma, Priya Singh vs Priya Sharma)
   * to enable realistic testing of exact matching, roll number priority, and fuzzy matching.
   */
  students: [
    { rollNumber: "001", studentId: "STU001", name: "Aarav Sharma", gender: "Male", email: "aarav.sharma@vitm.edu" },
    { rollNumber: "002", studentId: "STU002", name: "Aarav Verma", gender: "Male", email: "aarav.verma@vitm.edu" },
    { rollNumber: "003", studentId: "STU003", name: "Rahul Kumar", gender: "Male", email: "rahul.kumar@vitm.edu" },
    { rollNumber: "004", studentId: "STU004", name: "Rahul Singh", gender: "Male", email: "rahul.singh@vitm.edu" },
    { rollNumber: "005", studentId: "STU005", name: "Priya Singh", gender: "Female", email: "priya.singh@vitm.edu" },
    { rollNumber: "006", studentId: "STU006", name: "Priya Sharma", gender: "Female", email: "priya.sharma@vitm.edu" },
    { rollNumber: "007", studentId: "STU007", name: "Ankit Kumar", gender: "Male", email: "ankit.kumar@vitm.edu" },
    { rollNumber: "008", studentId: "STU008", name: "Ankit Sharma", gender: "Male", email: "ankit.sharma@vitm.edu" },
    { rollNumber: "009", studentId: "STU009", name: "Aman Kumar", gender: "Male", email: "aman.kumar@vitm.edu" },
    { rollNumber: "010", studentId: "STU010", name: "Aman Sharma", gender: "Male", email: "aman.sharma@vitm.edu" },
    { rollNumber: "011", studentId: "STU011", name: "Sneha Patel", gender: "Female", email: "sneha.patel@vitm.edu" },
    { rollNumber: "012", studentId: "STU012", name: "Sneha Gupta", gender: "Female", email: "sneha.gupta@vitm.edu" },
    { rollNumber: "013", studentId: "STU013", name: "Rohan Verma", gender: "Male", email: "rohan.verma@vitm.edu" },
    { rollNumber: "014", studentId: "STU014", name: "Rohan Sharma", gender: "Male", email: "rohan.sharma@vitm.edu" },
    { rollNumber: "015", studentId: "STU015", name: "Neha Gupta", gender: "Female", email: "neha.gupta@vitm.edu" },
    { rollNumber: "016", studentId: "STU016", name: "Neha Sharma", gender: "Female", email: "neha.sharma@vitm.edu" },
    { rollNumber: "017", studentId: "STU017", name: "Pooja Patel", gender: "Female", email: "pooja.patel@vitm.edu" },
    { rollNumber: "018", studentId: "STU018", name: "Pooja Verma", gender: "Female", email: "pooja.verma@vitm.edu" },
    { rollNumber: "019", studentId: "STU019", name: "Aditya Rao", gender: "Male", email: "aditya.rao@vitm.edu" },
    { rollNumber: "020", studentId: "STU020", name: "Aditya Singh", gender: "Male", email: "aditya.singh@vitm.edu" },
    { rollNumber: "021", studentId: "STU021", name: "Kavita Reddy", gender: "Female", email: "kavita.reddy@vitm.edu" },
    { rollNumber: "022", studentId: "STU022", name: "Vikram Joshi", gender: "Male", email: "vikram.joshi@vitm.edu" },
    { rollNumber: "023", studentId: "STU023", name: "Deepak Mishra", gender: "Male", email: "deepak.mishra@vitm.edu" },
    { rollNumber: "024", studentId: "STU024", name: "Divya Nair", gender: "Female", email: "divya.nair@vitm.edu" },
    { rollNumber: "025", studentId: "STU025", name: "Siddharth Malhotra", gender: "Male", email: "siddharth.m@vitm.edu" },
    { rollNumber: "026", studentId: "STU026", name: "Ritu Chauhan", gender: "Female", email: "ritu.chauhan@vitm.edu" },
    { rollNumber: "027", studentId: "STU027", name: "Manish Tiwari", gender: "Male", email: "manish.tiwari@vitm.edu" },
    { rollNumber: "028", studentId: "STU028", name: "Swati Deshmukh", gender: "Female", email: "swati.deshmukh@vitm.edu" },
    { rollNumber: "029", studentId: "STU029", name: "Karan Mehra", gender: "Male", email: "karan.mehra@vitm.edu" },
    { rollNumber: "030", studentId: "STU030", name: "Simran Kaur", gender: "Female", email: "simran.kaur@vitm.edu" },
    { rollNumber: "031", studentId: "STU031", name: "Harsh Vardhan", gender: "Male", email: "harsh.vardhan@vitm.edu" },
    { rollNumber: "032", studentId: "STU032", name: "Isha Bhatt", gender: "Female", email: "isha.bhatt@vitm.edu" },
    { rollNumber: "033", studentId: "STU033", name: "Gaurav Pandey", gender: "Male", email: "gaurav.pandey@vitm.edu" },
    { rollNumber: "034", studentId: "STU034", name: "Megha Saxena", gender: "Female", email: "megha.saxena@vitm.edu" },
    { rollNumber: "035", studentId: "STU035", name: "Nikhil Agrawal", gender: "Male", email: "nikhil.agrawal@vitm.edu" },
    { rollNumber: "036", studentId: "STU036", name: "Shreya Iyer", gender: "Female", email: "shreya.iyer@vitm.edu" },
    { rollNumber: "037", studentId: "STU037", name: "Abhishek Yadav", gender: "Male", email: "abhishek.yadav@vitm.edu" },
    { rollNumber: "038", studentId: "STU038", name: "Tanvi Kulkarni", gender: "Female", email: "tanvi.kulkarni@vitm.edu" },
    { rollNumber: "039", studentId: "STU039", name: "Mohit Chawla", gender: "Male", email: "mohit.chawla@vitm.edu" },
    { rollNumber: "040", studentId: "STU040", name: "Ananya Sen", gender: "Female", email: "ananya.sen@vitm.edu" },
    { rollNumber: "041", studentId: "STU041", name: "Varun Kapoor", gender: "Male", email: "varun.kapoor@vitm.edu" },
    { rollNumber: "042", studentId: "STU042", name: "Pallavi Roy", gender: "Female", email: "pallavi.roy@vitm.edu" },
    { rollNumber: "043", studentId: "STU043", name: "Suresh Pillai", gender: "Male", email: "suresh.pillai@vitm.edu" },
    { rollNumber: "044", studentId: "STU044", name: "Bhavna Das", gender: "Female", email: "bhavna.das@vitm.edu" },
    { rollNumber: "045", studentId: "STU045", name: "Rajeshwari Menon", gender: "Female", email: "rajeshwari.m@vitm.edu" },
    { rollNumber: "046", studentId: "STU046", name: "Pranav Choudhary", gender: "Male", email: "pranav.c@vitm.edu" },
    { rollNumber: "047", studentId: "STU047", name: "Sangeeta Rawat", gender: "Female", email: "sangeeta.rawat@vitm.edu" },
    { rollNumber: "048", studentId: "STU048", name: "Vivek Nambiar", gender: "Male", email: "vivek.nambiar@vitm.edu" },
    { rollNumber: "049", studentId: "STU049", name: "Kritika Jain", gender: "Female", email: "kritika.jain@vitm.edu" },
    { rollNumber: "050", studentId: "STU050", name: "Tarun Bhatia", gender: "Male", email: "tarun.bhatia@vitm.edu" },
    { rollNumber: "051", studentId: "STU051", name: "Akanksha Goswami", gender: "Female", email: "akanksha.g@vitm.edu" },
    { rollNumber: "052", studentId: "STU052", name: "Sanjay Hegde", gender: "Male", email: "sanjay.hegde@vitm.edu" },
    { rollNumber: "053", studentId: "STU053", name: "Rashmi Kulkarni", gender: "Female", email: "rashmi.k@vitm.edu" },
    { rollNumber: "054", studentId: "STU054", name: "Ashish Sengupta", gender: "Male", email: "ashish.s@vitm.edu" },
    { rollNumber: "055", studentId: "STU055", name: "Geeta Srinivasan", gender: "Female", email: "geeta.s@vitm.edu" },
    { rollNumber: "056", studentId: "STU056", name: "Sunil Khatri", gender: "Male", email: "sunil.khatri@vitm.edu" },
    { rollNumber: "057", studentId: "STU057", name: "Monika Barman", gender: "Female", email: "monika.barman@vitm.edu" },
    { rollNumber: "058", studentId: "STU058", name: "Arjun Nanda", gender: "Male", email: "arjun.nanda@vitm.edu" },
    { rollNumber: "059", studentId: "STU059", name: "Payal Mukherjee", gender: "Female", email: "payal.m@vitm.edu" },
    { rollNumber: "060", studentId: "STU060", name: "Yash Singhania", gender: "Male", email: "yash.singhania@vitm.edu" },
  ],

  // Initial attendance history records for demonstration
  attendanceHistory: [
    {
      id: "ATT-2026-0925",
      date: "2026-09-25",
      dateFormatted: "25 Sep 2026",
      classId: "BCA-2",
      className: "BCA - 2nd Year (Sec A)",
      subjectCode: "CS-402",
      subjectName: "Operating Systems & Shell Scripting",
      totalStudents: 60,
      present: 56,
      absent: 3,
      late: 1,
      unmarked: 0,
      submittedBy: "Prof. Rajesh Sharma",
      submittedAt: "2026-09-25 11:05 AM",
      status: "Submitted",
    },
    {
      id: "ATT-2026-0924",
      date: "2026-09-24",
      dateFormatted: "24 Sep 2026",
      classId: "BCA-2",
      className: "BCA - 2nd Year (Sec A)",
      subjectCode: "CS-401",
      subjectName: "Database Management Systems",
      totalStudents: 60,
      present: 58,
      absent: 2,
      late: 0,
      unmarked: 0,
      submittedBy: "Prof. Rajesh Sharma",
      submittedAt: "2026-09-24 10:55 AM",
      status: "Submitted",
    },
    {
      id: "ATT-2026-0923",
      date: "2026-09-23",
      dateFormatted: "23 Sep 2026",
      classId: "BCA-2",
      className: "BCA - 2nd Year (Sec A)",
      subjectCode: "CS-403",
      subjectName: "Object Oriented Programming via Java",
      totalStudents: 60,
      present: 54,
      absent: 5,
      late: 1,
      unmarked: 0,
      submittedBy: "Prof. Rajesh Sharma",
      submittedAt: "2026-09-23 02:40 PM",
      status: "Submitted",
    },
    {
      id: "ATT-2026-0922",
      date: "2026-09-22",
      dateFormatted: "22 Sep 2026",
      classId: "BCA-2",
      className: "BCA - 2nd Year (Sec A)",
      subjectCode: "CS-404",
      subjectName: "Computer Networks & Security",
      totalStudents: 60,
      present: 55,
      absent: 4,
      late: 1,
      unmarked: 0,
      submittedBy: "Prof. Rajesh Sharma",
      submittedAt: "2026-09-22 12:10 PM",
      status: "Submitted",
    },
  ],
};

// Expose globally for both app.js and Chrome Extension integration testing
if (typeof window !== "undefined") {
  window.MOCK_DATA = MOCK_DATA;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = MOCK_DATA;
}
